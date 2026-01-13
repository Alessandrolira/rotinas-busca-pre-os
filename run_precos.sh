#!/bin/bash

DATA=$(date +"%Y-%m-%d_%H-%M")

python /app/atualizar_precos_amil.py \
 >> /logs/precos_$DATA.log \
 2>> /logs/precos_ERROR_$DATA.txt
