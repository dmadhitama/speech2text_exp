#!/bin/bash
# /home/benedictus_aryo/miniconda3/envs/stt_soap/bin/streamlit run /home/benedictus_aryo/speech2text_exp/streamlit_app_poc.py --server.port 8080 --server.address 127.0.0.1

PORT=3389
HOST=0.0.0.0
/home/benedictus_aryo/miniconda3/envs/stt_soap/bin/uvicorn main:app --reload --host $HOST --port $PORT --ssl-keyfile /home/benedictus_aryo/speech2text_exp/selfsigned.key --ssl-certfile /home/benedictus_aryo/speech2text_exp/selfsigned.crt
# /home/benedictus_aryo/miniconda3/envs/stt_soap/bin/uvicorn main:app --reload --host $HOST --port $PORT --ssl-keyfile /home/benedictus_aryo/speech2text_exp/key.pem --ssl-certfile /home/benedictus_aryo/speech2text_exp/cert.pem
