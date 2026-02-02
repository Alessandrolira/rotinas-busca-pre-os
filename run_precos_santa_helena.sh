#!/bin/bash

DATA=$(date +"%Y-%m-%d_%H-%M")

python /app/atualizar_precos_santa_helena.py \
 >> /logs/rede_$DATA.log \
 2>> /logs/rede_ERROR_$DATA.txt
