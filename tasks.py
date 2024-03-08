import requests
import traceback
import os
import json
import shutil
import pytesseract
from time import sleep
from subprocess import call
from django.utils.text import slugify
from huey.contrib.djhuey import db_task
from timeit import default_timer as timer
from corpus import *

REGISTRY = {
    "OCR Document with Tesseract 5": {
        "version": "0.1",
        "jobsite_type": "HUEY",
        "track_provenance": True,
        "create_report": True,
        "content_type": "Document",
        "configuration": {
            "parameters": {
                "name": {
                    "value": "",
                    "type": "text",
                    "label": "Unique Name for this OCR Job"
                },
                "collection": {
                    "value": "",
                    "type": "page_file_collection",
                    "label": "Page Image Collection",
                    "note": "Be sure to select a collection consisting of images."
                },
                "pageset": {
                    "value": "",
                    "type": "document_pageset",
                    "label": "Page Set",
                    "note": 'Choose "All Pages" to OCR every page, or select a page set to OCR a subset of pages.'
                },
                "primary_witness": {
                    "label": "Make Primary Witness?",
                    "type": "choice",
                    "choices": [
                        "Yes",
                        "No"
                    ],
                    "value": "Yes",
                    "note": "If you have not yet OCR'd this document, or if you'd like to replace existing OCR results as the primary witness for this document, this should remain set to 'Yes.'"
                },
                "language_model": {
                    "value": "",
                    "label": "Tesseract Language Model",
                    "type": "xref",
                    "content_type": "TesseractLanguageModel"
                }
            },
        },
        "module": 'plugins.tesseract.tasks',
        "functions": ['ocr_document_with_tesseract', 'complete_ocr_document_with_tesseract']
    },
    "Register Tesseract Language Models": {
        "version": "0.2",
        "jobsite_type": "HUEY",
        "track_provenance": True,
        "create_report": False,
        "content_type": "Corpus",
        "configuration": {
            "parameters": {
                "download_models": {
                    "label": "Download Existing Language Models?",
                    "type": "choice",
                    "choices": [
                        "Yes",
                        "No"
                    ],
                    "value": "Yes",
                    "note": "These models come from here: https://github.com/tesseract-ocr/tessdata_best"
                },
            },
        },
        "module": 'plugins.tesseract.tasks',
        "functions": ['register_language_models']
    },
    "Train Tesseract Language Model": {
        "version": "0.1",
        "jobsite_type": "HUEY",
        "track_provenance": True,
        "create_report": False,
        "content_type": "Document",
        "configuration": {
            "parameters": {
                "name": {
                    "value": "",
                    "label": "New Tesseract Language Model",
                    "type": "pep8_text",
                    "note": "Leave blank if you're improving an existing model."
                },
                "base_model": {
                    "value": "",
                    "label": "Base Tesseract Language Model",
                    "type": "xref",
                    "content_type": "TesseractLanguageModel",
                    "note": "The model to base your new model on, or the model you wish to improve."
                },
                "transcription_project": {
                    "value": "",
                    "label": "Transcription Project",
                    "type": "xref",
                    "content_type": "TranscriptionProject",
                    "note": "The transcription project to use for training data."
                }
            },
        },
        "module": 'plugins.tesseract.tasks',
        "functions": ['train_language_model']
    }
}

TESSERACT_FONT_DIR = '/usr/share/tesseract-ocr/5/tessdata'
TRAINING_TIMEOUT_MINUTES_PER_PAGE = 5


@db_task(priority=2)
def ocr_document_with_tesseract(job_id):
    job = Job(job_id)
    job.set_status('running')

    try:
        page_file_collection_key = job.get_param_value('collection')
        pageset_key = job.get_param_value('pageset')
        page_files = job.content.page_file_collections[page_file_collection_key]['page_files']
        primary_witness = job.configuration['parameters']['primary_witness']['value'] == 'Yes'
        language_model_id = job.get_param_value('language_model')
        language_model = job.corpus.get_content('TesseractLanguageModel', language_model_id)

        font_dir = os.environ.get('CRP_TESSERACT_FONT_DIR', None)
        if font_dir and os.path.exists(font_dir):
            requirements = ["configs", "tessconfigs"]
            for requirement in requirements:
                if not os.path.exists(f"{font_dir}/{requirement}"):
                    os.system(f"cp -r {TESSERACT_FONT_DIR}/{requirement} {font_dir}/{requirement}")

            os.environ['TESSDATA_PREFIX'] = font_dir

        ref_nos = []
        if pageset_key == "none":
            ref_nos = page_files.ordered_ref_nos
        elif pageset_key in job.content.page_sets:
            ref_nos = [ref_no for ref_no in page_files.ordered_ref_nos if ref_no in job.content.page_sets[pageset_key].ref_nos]

        num_pages = len(ref_nos)

        if num_pages > 0:
            job.report("Attempting to OCR {0} pages for page file collection {1}.".format(num_pages, page_file_collection_key))
            if pageset_key != "none":
                job.report("Limiting pages to those found in page set {0}.".format(job.content.page_sets[pageset_key].label))

            if primary_witness:
                unset_primary(job.content, 'plain text')
                unset_primary(job.content, 'hocr')
                job.content.save()

            for ref_no in ref_nos:
                huey_task = ocr_page_with_tesseract(job_id, ref_no, primary_witness, language_model.code)
                job.add_process(huey_task.id)
        else:
            job.report("No valid pages found to OCR!")

    except:
        error = traceback.format_exc()
        print(error)
        job.complete('error', error_msg=error)


@db_task(priority=1, context=True)
def ocr_page_with_tesseract(job_id, assigned_ref_no, primary_witness, language_model, task=None):
    job = Job(job_id)
    ocr_job_name = job.get_param_value('name')
    page_file_collection_key = job.get_param_value('collection')
    page_files = job.content.page_file_collections[page_file_collection_key]['page_files']
    successful = False
    time_start = timer()

    for ref_no, file in page_files:
        if ref_no == assigned_ref_no:
            page_file_dir = f"{job.content.path}/pages/{ref_no}"
            os.makedirs(page_file_dir, exist_ok=True)

            if os.path.exists(file['path']) or file['iiif_info']:
                # base path for different outputs
                page_file_results = f"{page_file_dir}/Tesseract5_{slugify(ocr_job_name)}_{ref_no}"

                page_file_path = file['path']
                if file['iiif_info']:
                    image_width = file['width']
                    if image_width > 3000:
                        image_width = 3000

                    region = "full"
                    if 'fixed_region' in file['iiif_info']:
                        fixed_r = file['iiif_info']['fixed_region']
                        region = "{x},{y},{w},{h}".format(
                            x=fixed_r['x'],
                            y=fixed_r['y'],
                            w=fixed_r['w'],
                            h=fixed_r['h']
                        )

                    download_url = "{id}/{region}/{width},/0/default.png".format(
                        id=file['path'],
                        region=region,
                        width=image_width
                    )
                    img_download = requests.get(download_url, stream=True)
                    page_file_path = "{0}/temp_img.png".format(page_file_dir)
                    with open(page_file_path, 'wb') as img_out:
                        shutil.copyfileobj(img_download.raw, img_out)

                os.environ['OMP_THREAD_LIMIT'] = '1'
                command = [
                    "tesseract",
                    page_file_path,
                    page_file_results,
                    "-l", language_model,
                    "--psm", "1",
                    "hocr", "txt"
                ]

                print(" ".join(command))

                try:
                    if call(command, timeout=5 * 60) == 0:
                        txt_file_obj = File.process(
                            page_file_results + '.txt',
                            desc='Plain Text',
                            prov_type=f'Tesseract5 OCR Job ({ocr_job_name})',
                            prov_id=str(job_id),
                            primary=primary_witness
                        )
                        if txt_file_obj:
                            job.content.save_page_file(ref_no, txt_file_obj)

                        hocr_file_obj = File.process(
                            page_file_results + '.hocr',
                            desc='HOCR',
                            prov_type=f'Tesseract5 OCR Job ({ocr_job_name})',
                            prov_id=str(job_id),
                            primary=primary_witness
                        )
                        if hocr_file_obj:
                            job.content.save_page_file(ref_no, hocr_file_obj)

                        successful = True
                except:
                    job.report("Error OCR'ing page {0}:".format(assigned_ref_no))
                    job.report(traceback.format_exc())

                if file['iiif_info'] and os.path.exists(page_file_path):
                    os.remove(page_file_path)

            break

    if task:
        time_stop = timer()
        if successful:
            job.report("Tesseract OCR'd page {0} in {1} seconds.".format(assigned_ref_no, time_stop - time_start))
        job.complete_process(task.id)


@db_task(priority=2)
def complete_ocr_document_with_tesseract(job_id):
    job = Job(job_id)
    job.content.save(index_pages=True)
    job.complete(status='complete')


@db_task(priority=2)
def register_language_models(job_id):
    job = Job(job_id)
    download_models = job.get_param_value('download_models') == 'Yes'

    job.set_status("running")

    code_language_map = {}
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    language_code_json = f"{plugin_dir}/language_codes.json"
    if os.path.exists(language_code_json):
        with open(language_code_json, 'r', encoding='utf-8') as lang_codes_in:
            code_language_map = json.load(lang_codes_in)

    font_dir = os.environ.get('CRP_TESSERACT_FONT_DIR')

    if font_dir and os.path.exists(font_dir):
        if download_models:
            os.chdir(font_dir)
            os.system("git clone --depth 1 https://github.com/tesseract-ocr/tessdata_best.git")
            clone_dir = f"{font_dir}/tessdata_best"
            if os.path.exists(clone_dir):
                models = [m for m in os.listdir(clone_dir) if m.endswith('.traineddata')]
                for model in models:
                    from_path = f"{clone_dir}/{model}"
                    to_path = f"{font_dir}/{model}"
                    if not os.path.exists(to_path):
                        shutil.move(from_path, to_path)
                shutil.rmtree(clone_dir)

        langs = [l.replace('.traineddata', '') for l in os.listdir(font_dir) if l.endswith('.traineddata')]
    else:
        langs = pytesseract.get_languages(config='')

    for lang in langs:
        model = job.corpus.get_or_create_content('TesseractLanguageModel', {
            'code': lang,
            'name': code_language_map.get(lang, lang),
        })

    job.complete(status='complete')


@db_task(priority=2)
def train_language_model(job_id):
    job = Job(job_id)
    model_name = job.get_param_value('name')

    base_model_id = job.get_param_value('base_model')
    base_model = job.corpus.get_content('TesseractLanguageModel', base_model_id)
    if not model_name:
        model_name = base_model.code

    trans_project_id = job.get_param_value('transcription_project')
    trans_project = job.corpus.get_content('TranscriptionProject', trans_project_id)

    transom_dir = os.environ.get('CRP_TESSERACT_TRAINING_TRANSOM', None)
    font_dir = os.environ.get('CRP_TESSERACT_FONT_DIR', None)

    job.set_status('running', percent_complete=1)
    error_messages = []
    completed = False

    if transom_dir and font_dir and os.path.exists(transom_dir) and os.path.exists(font_dir):
        doc = trans_project.document
        if trans_project.pageset in doc.page_sets and trans_project.image_pfc:
            pageset = trans_project.pageset
            image_pfc = doc.get_page_file_collection(trans_project.image_pfc, pageset)
            transcriptions = job.corpus.get_content('Transcription', {'project': trans_project_id})
            training_set_file = f"{transom_dir}/{model_name}_trainingset.json"

            if os.path.exists(training_set_file):
                error_messages.append(f"A training set for model {model_name} is either already in process or has errored out. Please either wait for the process to complete or delete the file f{training_set_file}.")
            else:
                training_set = {
                    "name": model_name,
                    "base_model": base_model.code,
                    "images": []
                }

                for trans in transcriptions:
                    if trans.data:
                        image_filename = f"{transom_dir}/{model_name}_{trans.page_refno}.png"
                        image_file = image_pfc['page_files'][trans.page_refno]

                        if image_file['path'].startswith('http'):
                            rotation = 0
                            if 'iiif_info' in image_file and 'fixed_rotation' in image_file['iiif_info']:
                                rotation = image_file['iiif_info']['fixed_rotation']

                            iiif_url = f"{image_file['path']}/full/max/{rotation}/default.png"

                            r = requests.get(iiif_url, stream=True)
                            if r.status_code == 200:
                                with open(image_filename, 'wb') as f:
                                    for chunk in r:
                                        f.write(chunk)

                        elif image_file['path'].startswith('/') and os.path.exists(image_file['path']):
                            shutil.copyfile(image_file['path'], image_filename)

                        training_set['images'].append({
                            'image': os.path.basename(image_filename),
                            'lines': json.loads(trans.data)
                        })

                if training_set['images']:
                    with open(training_set_file, 'w', encoding='utf-8') as trans_out:
                        json.dump(training_set, trans_out, indent=4)

                    image_count = len(training_set['images'])
                    slept_seconds = 0
                    timeout_seconds = image_count * TRAINING_TIMEOUT_MINUTES_PER_PAGE * 60
                    while os.path.exists(training_set_file) and slept_seconds < timeout_seconds:
                        sleep(30)
                        slept_seconds += 30
                        if slept_seconds % 60 == 0:
                            job.set_status('running', percent_complete=int((slept_seconds / timeout_seconds) * 100))

                    if os.path.exists(training_set_file):
                        error_messages.append(f"Training timed out on model {model_name}!")
                        os.remove(training_set_file)
                    elif not os.path.exists(f"{font_dir}/{model_name}.traineddata"):
                        error_messages.append(f"Tesseract trainer failed to produce model for {model_name}!")
                    else:
                        model = job.corpus.get_or_create_content('TesseractLanguageModel', {
                            'name': model_name,
                            'code': model_name,
                            'base_model': base_model.id
                        })
                        if model.pages_trained:
                            model.pages_trained += image_count
                        else:
                            model.pages_trained = image_count
                        model.save()
                        job.complete('complete')
                        completed = True

        else:
            error_messages.append("The transcription pageset no longer exists for this document.")
    else:
        error_messages.append("Transom directory for Tesseract trainer doesn't exist!")

    if not completed:
        job.complete('error', error_msg=" ".join(error_messages))


def unset_primary(doc, file_type):
    page_keys = list(doc.pages.keys())
    for page_key in page_keys:
        file_keys = list(doc.pages[page_key].files.keys())
        for file_key in file_keys:
            if doc.pages[page_key].files[file_key].primary_witness and file_type.lower() in doc.pages[page_key].files[file_key].description.lower():
                doc.pages[page_key].files[file_key].primary_witness = False


