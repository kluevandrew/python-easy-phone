# PJSIP Python EasyPhone
> Call via VoIP using only one command

docker run -it --rm --net=host python-easy-phone -s <sip.example.com> -l <username> -p <passowrd> <phone> demo.wav
docker run -it --rm --net=host -v audio.wav:/audio.wav python-easy-phone -s <sip.example.com> -l <username> -p <passowrd> <phone> /audio.wav