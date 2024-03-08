# tesseract

The Corpora plugin for performing OCR and font training with Tesseract 5.

## Configuration for OCR Jobs

To run Tesseract OCR jobs from within Corpora, you must mount the directory containing this file into the `/apps/corpora/plugins/tesseract` directory
inside the Corpora container. You must then ensure that `tesseract` is listed among the comma-separated list
of plugins enabled via the `CRP_INSTALLED_PLUGINS` environment variable for Corpora.

Once this happens, the `OCR Document using Tesseract 5` task should be available to run by clicking `Run Job`
on the page for a specific document (created using Corpora's built-in `Document` plugin).

Because the `OCR Document using Tesseract 5` job requires specifying a language (or trained OCR model, or font) to use, you must 
also define the `CRP_TESSERACT_FONT_DIR` environment variable in Corpora to specify where trained fonts will be
downloaded or saved after training inside the Corpora container. *Note*: The path you specify should be a shared
volume that can also be mounted inside the `TessTrainer` container detailed below if you plan on training fonts.

Because Tesseract models can be large, no default models are included with the plugin. Also, in order to keep track of
the fonts for OCR/training purposes, the `TesseractLanguageModel` content type must be defined. The best way to both
define the `TesseractLanguageModel` content type and also download models for most languages is to run the `Register Tesseract Language Models`
task. This can be done by going to the `Admin` tab of a corpus page and clicking `Run Job.` When you leave `Yes` selected for the 
`Download Existing Language Models?` parameter before launching the job, it will ensure that the language models in this 
Git repository are downloaded and installed: https://github.com/tesseract-ocr/tessdata_best

## Configuration for Font Training

Assuming you've performed all the configuration needed for OCR jobs (above), you'll also need to define the `CRP_TESSERACT_TRAINING_TRANSOM` 
environment variable for the Corpora container. This variable is a path to the directory that will be used by Corpora to
place image files and special .json files for the `TessTrainer` Docker container to use for training new fonts. This
directory will need to be shared by both the Corpora container and the TessTrainer container.

The TessTrainer container must be running for training to occur, and it must have the following shared volumes mounted:

* `/usr/local/share/tessdata`: This should be the same volume as the one mounted inside the Corpora container at the path
    specified by the `CRP_TESSERACT_FONT_DIR` environment variable. It's where base models will be found for training new models,
    and also where newly trained models will be deposited.
* `/root/transom`: This should be the same volume as the one mounted by Corpora at the path specified by the `CRP_TESSERACT_TRAINING_TRANSOM`
    directory. It's where image files and .json files describing the training job will be deposited by Corpora.

## Example Docker Compose File Service Definition for the TessTrainer Container

```
  tesstrainer:
    image: bptarpley/tesstrainer
    volumes:
      - /path/to/shared/font/directory:/usr/local/share/tessdata
      - /path/to/job/file/transom:/root/transom
      # The below path is optional, but it will allow you to override the code for performing the training:
      - /path/to/tesseract/plugin/trainer/do_training.py:/root/do_training.py
```

The image for the TessTrainer container lives in Docker Hub (bptarpley/tesstrainer), but can also be built using the Dockerfile
supplied with this plugin. To do so, simply replace the line `image: bptarpley/tesstrainer` with `build: /path/to/tesseract/plugin/trainer`.
