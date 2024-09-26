#!/bin/bash
set -e

#echo docker repo $1
URL=`echo "$1"`

# Получаем имя текущей ветки Git
echo generate version file
branch=$(git rev-parse --abbrev-ref HEAD)

# Создаем папку version и info.json внутри неё
mkdir -p version
info_file="version/info.json"

# Получаем время создания и hash последнего коммита
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
commit_hash=$(git rev-parse HEAD)
commit_author=$(git log -1 --format='%an')

# Создаем содержимое info.json
cat << EOF > $info_file
{
  "branch": "$branch",
  "timestamp": "$timestamp",
  "commit_hash": "$commit_hash",
  "commit_author": "$commit_author"
}
EOF

echo Builing docker image ...
LABEL=`echo "$branch" | tr '[:upper:]' '[:lower:]'`
echo $LABEL

## Генерируем имя образа Docker
docker_image="$URL:$branch"

## Собираем Docker образ
docker build -t $docker_image .


# Пушим Docker образ в указанный URL
docker push $docker_image