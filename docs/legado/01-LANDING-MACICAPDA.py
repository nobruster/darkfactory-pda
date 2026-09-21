#!/usr/bin/env python
# coding: utf-8

# In[11]:


import io
import os
import time
import urllib.request
import zipfile
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# ---------------------------------------------------------------------------
# Configuracoes
# ---------------------------------------------------------------------------

URL = (
    "https://armazenamento-dadosabertos.s3.sa-east-1.amazonaws.com/"
    "PDA_2025_2027/Grupos_de_dados/Benef%C3%ADcios+emitidos/"
    "D.SDA.PDA.003.EMI.202601.CSV.ZIP"
)

#CACHE_DIR   = "/opt/bitnami/spark/work/dados-abertos"
CACHE_DIR   = "/opt/bitnami/spark/work"
CSV_NAME    = "D.SDA.PDA.003.EMI.202601.csv"
csv_path    = os.path.join(CACHE_DIR, CSV_NAME)
BUCKET      = "landing"
MINIO_PATH  = f"s3a://{BUCKET}/pda/beneficios-emitidos/202601/"
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Download + extração (pula se CSV já existe no cache local)
# ---------------------------------------------------------------------------
'''
print("=" * 60)

if os.path.exists(csv_path):
    size_mb = os.path.getsize(csv_path) / (1024 ** 2)
    print(f"1. Cache encontrado: {csv_path} ({size_mb:.1f} MB) — pulando download")
else:
    print("1. Baixando ZIP da fonte pública...")
    t0 = time.time()
    zip_bytes = urllib.request.urlopen(URL).read()
    print(f"   Baixado: {len(zip_bytes) / (1024**2):.1f} MB em {time.time()-t0:.1f}s")
    print("2. Extraindo CSV...")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_files = [f for f in zf.namelist() if f.lower().endswith(".csv")]
        zf.extract(csv_files[0], CACHE_DIR)
        csv_path = os.path.join(CACHE_DIR, csv_files[0])
    print(f"   Extraído: {csv_path} ({os.path.getsize(csv_path)/(1024**2):.1f} MB)")

    del zip_bytes 
'''


# In[ ]:





# In[16]:


# ---------------------------------------------------------------------------
# 2. Detectar separador
# ---------------------------------------------------------------------------
with open(csv_path, "r", encoding="latin-1") as f:
    header = f.readline()
sep = next((s for s in [";", ",", "\t", "|"] if header.count(s) > 2), ";")
print(f"\n3. Separador detectado: '{sep}'")


# In[12]:


# ---------------------------------------------------------------------------
# 3. SparkSession (usa spark-defaults.conf para conexão S3A/MinIO)
# ---------------------------------------------------------------------------
print("\n4. Iniciando SparkSession...")
spark = SparkSession.builder.appName("Landing-PDA-Beneficios-202601") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio1:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.path.style.access", True) \
    .config("spark.hadoop.fs.s3a.fast.upload", True) \
    .config("spark.hadoop.fs.s3a.multipart.size", 104857600) \
    .config("fs.s3a.connection.maximum", 100) \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")\
    .config("spark.delta.logStore.class", "org.apache.spark.sql.delta.storage.S3SingleDriverLogStore")\
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")\
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")\
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")\
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")


# In[13]:


# Calcula partições em tempo de execução com base nos cores reais do cluster.
# defaultParallelism = total de cores alocados para esta aplicação (reflete spark.cores.max
# ou o que o cluster conseguiu alocar de fato no momento do submit).
total_cores     = spark.sparkContext.defaultParallelism
shuffle_parts   = max(4, total_cores * 2)   # mínimo 4 mesmo em clusters muito pequenos
n_output_files  = max(1, total_cores)        # 1 arquivo por core → paralelismo máximo na escrita

spark.conf.set("spark.sql.shuffle.partitions", shuffle_parts)

print(f"   Cores alocados      : {total_cores}")
print(f"   shuffle.partitions  : {shuffle_parts}  (cores × 2)")
print(f"   Arquivos de saída   : {n_output_files} (coalesce = 1 por core)")


# In[14]:


# ---------------------------------------------------------------------------
# 4. Criar bucket 'landing' no MinIO (via Hadoop FileSystem S3A)
# ---------------------------------------------------------------------------

print(f"\n5. Verificando bucket '{BUCKET}' no MinIO...")
jvm         = spark.sparkContext._jvm
hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
uri         = jvm.java.net.URI.create(f"s3a://{BUCKET}")
fs          = jvm.org.apache.hadoop.fs.FileSystem.get(uri, hadoop_conf)
bucket_path = jvm.org.apache.hadoop.fs.Path(f"s3a://{BUCKET}/")

if not fs.exists(bucket_path):
    fs.mkdirs(bucket_path)
    print(f"   Bucket '{BUCKET}' criado.")
else:
    print(f"   Bucket '{BUCKET}' já existe.") 


# In[17]:


# ---------------------------------------------------------------------------
# 5. Ler CSV — landing = raw, inferSchema=False (preserva dado original)
# ---------------------------------------------------------------------------
print("\n6. Lendo CSV com Spark...")
df = spark.read.csv(
    csv_path,
    header=True,
    inferSchema=False,      # landing zone: sem inferencia de tipo
    sep=sep,
    encoding="ISO-8859-1",
)


# In[18]:


df.show(3)


# In[19]:


# Desambiguar colunas duplicadas ('Espécie' aparece 2x no dataset)
seen, new_cols = {}, []
for c in df.columns:
    if c in seen:
        seen[c] += 1
        new_cols.append(f"{c}_{seen[c]}")
    else:
        seen[c] = 0
        new_cols.append(c)
df = df.toDF(*new_cols)

print(f"   Colunas ({len(df.columns)}): {df.columns}")


# In[20]:


# ---------------------------------------------------------------------------
# 6. Gravar no MinIO como Parquet (overwrite para idempotência)
# ---------------------------------------------------------------------------
print(f"\n7. Gravando em {MINIO_PATH} ...")
t0 = time.time()
df.coalesce(n_output_files).write.mode("overwrite").parquet(MINIO_PATH)
print(f"   Gravação concluída em {time.time()-t0:.1f}s")


# In[ ]:


'''spark = SparkSession \
    .builder \
    .appName("etl-enriched-users-analysis-py") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio1:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.path.style.access", True) \
    .config("spark.hadoop.fs.s3a.fast.upload", True) \
    .config("spark.hadoop.fs.s3a.multipart.size", 104857600) \
    .config("fs.s3a.connection.maximum", 100) \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.delta.logStore.class", "org.apache.spark.sql.delta.storage.S3SingleDriverLogStore") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config('spark.hadoop.fs.s3a.aws.credentials.provider', 'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider') \
    .getOrCreate()'''


# In[ ]:




