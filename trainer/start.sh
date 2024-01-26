docker run -it \
  -v /Users/bptarpley/corpora/import/tesstrainer/fonts:/usr/local/share/tessdata \
  -v /Users/bptarpley/corpora/import/tesstrainer/transom:/root/transom \
  -v ./do_training.py:/root/do_training.py \
  bptarpley/tesstrainer ../reflex -r '_trainingset\.json$' python3 /root/do_training.py {}

  #-v /Users/bptarpley/corpora/import/tesstrainer/training:/root/tesseract/tesstrain/data \
  #bptarpley/tesstrainer /bin/bash

