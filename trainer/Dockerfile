FROM ubuntu:22.04

RUN apt update
RUN apt install -y git g++ make autoconf automake libtool pkg-config libpng-dev libjpeg8-dev libtiff5-dev zlib1g-dev \
    libwebpdemux2 libwebp-dev libopenjp2-7-dev libgif-dev libarchive-dev libcurl4-openssl-dev libicu-dev \
    libpango1.0-dev libcairo2-dev libleptonica-dev bc python3-pip wget bc

WORKDIR /root
RUN git clone --depth 1 https://github.com/tesseract-ocr/tesseract.git
WORKDIR /root/tesseract
RUN /root/tesseract/autogen.sh
RUN /root/tesseract/configure
RUN make
RUN make install
RUN ldconfig

RUN make training
RUN make training-install

RUN git clone --depth 1 https://github.com/tesseract-ocr/tesstrain.git
WORKDIR /root/tesseract/tesstrain
RUN pip install -r requirements.txt
RUN make tesseract-langdata

WORKDIR /root
RUN wget https://github.com/cespare/reflex/releases/download/v0.3.1/reflex_linux_amd64.tar.gz
RUN tar -xf reflex_linux_amd64.tar.gz
RUN cp ./reflex_linux_amd64/reflex ./
RUN rm -r ./reflex_linux*

COPY ./do_training.py /root/do_training.py
WORKDIR /root/transom
ENV TESSDATA_PREFIX=/root/tesseract/tessdata

CMD ../reflex -r '_trainingset\.json$' python3 /root/do_training.py {}
