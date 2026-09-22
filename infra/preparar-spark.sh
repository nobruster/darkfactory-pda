#!/bin/sh
# Prepara o contêiner Spark: PyYAML e os jars do S3A.
#
# Fica num arquivo, não inline no compose: o Compose interpreta $VAR como
# variável DELE e substitui por vazio antes do shell ver. A primeira versão
# virou `curl -o "" ""` e baixou nada, com S3A_JARS=0.
#
# A versão do hadoop-aws tem de ser EXATAMENTE a do Hadoop embutido —
# 3.3.4, conferido em /opt/spark/jars/hadoop-client-api-3.3.4.jar.
# Descasar produz NoSuchMethodError em runtime, não no build.
set -e

pip install --quiet --no-cache-dir pyyaml==6.0.2

MAVEN=https://repo1.maven.org/maven2
JARS="org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar"

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

exec sleep infinity
