#!/bin/sh
# Prepara o contêiner Spark: PyYAML, pytest e os jars do S3A.
#
# Fica num arquivo, não inline no compose: o Compose interpreta $VAR como
# variável DELE e substitui por vazio antes do shell ver. A primeira versão
# virou `curl -o "" ""` e baixou nada, com S3A_JARS=0.
#
# A versão do hadoop-aws tem de ser EXATAMENTE a do Hadoop embutido —
# 3.3.4, conferido em /opt/spark/jars/hadoop-client-api-3.3.4.jar.
# Descasar produz NoSuchMethodError em runtime, não no build.
#
# ⚠️ pytest entra AQUI, e não numa tarefa do Pass 8, porque o contrato de
# runtime nega rede ao agente — `net.egress: False`, `policy.network: deny`
# — corretamente, já que ele escreve código. Uma tarefa que precisasse
# instalar qualquer coisa seria impossível por construção: a Bronze gastou
# os 600s inteiros e escreveu zero arquivos tentando exatamente isso, e o
# receipt saiu `result: blocked`.
#
# Preparar o ambiente é pré-requisito do HOST, como docker e git já são.
# O eval USA o ambiente; não o constrói.
set -e

pip install --quiet --no-cache-dir pyyaml==6.0.2 pytest==8.3.4

# psycopg — a projeção da ontologia no Postgres (serviço pda-postgres).
# Entra aqui pelo mesmo motivo do pytest: o agente do loop não tem rede.
# [binary] traz a libpq junto; sem ele o import pede a libpq do sistema.
pip install --quiet --no-cache-dir "psycopg[binary]==3.2.3"

# Delta Lake — as camadas do medalhão gravam em Delta (decisão do dono,
# 2026-09-23). 3.2.1 é a linha do Delta para Spark 3.5 / Scala 2.12; o
# pip vai SEM dependências, porque puxaria outro pyspark por cima do 3.5.9.
pip install --quiet --no-cache-dir --no-deps delta-spark==3.2.1

MAVEN=https://repo1.maven.org/maven2
JARS="org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar
io/delta/delta-spark_2.12/3.2.1/delta-spark_2.12-3.2.1.jar
io/delta/delta-storage/3.2.1/delta-storage-3.2.1.jar"

echo "$JARS" | while read -r caminho; do
  [ -n "$caminho" ] || continue
  nome=$(basename "$caminho")
  if [ -f "/opt/spark/jars/$nome" ]; then
    echo "  $nome já existe"
  else
    echo "  baixando $nome..."
    curl -fsSL -o "/opt/spark/jars/$nome" "$MAVEN/$caminho"
  fi
done

n=$(ls /opt/spark/jars/ | grep -cE "hadoop-aws|aws-java-sdk-bundle" || true)
echo "S3A_JARS=$n"
[ "$n" -eq 2 ] || { echo "S3A=INCOMPLETO"; exit 1; }
echo "S3A=OK"

d=$(ls /opt/spark/jars/ | grep -cE "^delta-(spark_2\.12|storage)-3\.2\.1\.jar$" || true)
echo "DELTA_JARS=$d"
[ "$d" -eq 2 ] || { echo "DELTA=INCOMPLETO"; exit 1; }
python3 -c "import delta" || { echo "DELTA=SEM_PYTHON"; exit 1; }
echo "DELTA=OK"

exec sleep infinity
