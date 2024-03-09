#!/usr/bin/env python3
"""Reddit Data Scrapper Service
    ©2024, Ovais Quraishi

    Collects submissions, comments for each submission, author of each submission,
    author of each comment to each submission, and all comments for each author.
    Also, subscribes to subreddit that a submission was posted to

    Uses Gunicorn WSGI

    Install Python Modules:
        > pip3 install -r requirements.txt

    Get Reddit API key: https://www.reddit.com/wiki/api/

    Gen SSL key/cert
        > openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 3650

    Create Database and tables:
        reddit.sql

    Generate Flask App Secret Key:
        >  python -c 'import secrets; print(secrets.token_hex())'

    Update setup.config with pertinent information (see setup.config.template)

    Run Service:
    (see https://docs.gunicorn.org/en/stable/settings.html for config details)

        > gunicorn --certfile=cert.pem \
                   --keyfile=key.pem \
                   --bind 0.0.0.0:5000 \
                   reddit_gunicorn:app \
                   --timeout 2592000 \
                   --threads 4 \
                   --reload

    Customize it to your hearts content!

    LICENSE: The 3-Clause BSD License - license.txt

    TODO:
        - Add Swagger Docs
        - Add long running task queue
            - Queue: task_id, task_status, end_point
            - Kafka
        - Revisit Endpoint logic add robust error handling
        - Add scheduler app - to schedule some of these events
            - scheduler checks whether or not a similar tasks exists
        - Add logic to handle list of lists with NUM_ELEMENTS_CHUNK elementsimport configparser
"""

import asyncio
import hashlib
import json
import logging

import httpx
import langdetect
from langdetect import detect
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from prawcore import exceptions
from ollama import AsyncClient

# Import required local modules
from config import get_config
from database import db_get_authors
from database import insert_data_into_table
from database import get_new_data_ids
from database import get_select_query_results
from database import get_select_query_results2
from database import db_get_post_ids
from database import db_get_comment_ids
from encryption import encrypt_text, decrypt_text
from reddit_api import create_reddit_instance
from utils import unix_ts_str, sleep_to_avoid_429, sanitize_string, ts_int_to_dt_obj
from utils import serialize_datetime

app = Flask('ZOllama-GPT')

# constants
CONFIG = get_config()

NUM_ELEMENTS_CHUNK = 25
LLMS = CONFIG.get('service','LLMS').split(',')
MEDLLMS = CONFIG.get('service','MEDLLMS').split(',')

# Flask app config
app.config.update(
                  JWT_SECRET_KEY=CONFIG.get('service', 'JWT_SECRET_KEY'),
                  SECRET_KEY=CONFIG.get('service', 'APP_SECRET_KEY'),
                  PERMANENT_SESSION_LIFETIME=172800 #2 days
                 )
jwt = JWTManager(app)

# Reddit authentication
REDDIT = create_reddit_instance()

@app.route('/login', methods=['POST'])
def login():
    """Generate JWT
    """

    secret = request.json.get('api_key')

    if secret != CONFIG.get('service','SRVC_SHARED_SECRET'):  # if the secret matches
        return jsonify({"message": "Invalid secret"}), 401

    # generate access token
    access_token = create_access_token(identity=CONFIG.get('service','IDENTITY'))
    return jsonify(access_token=access_token), 200

@app.route('/analyze_post', methods=['GET'])
@jwt_required()
def analyze_post_endpoint():
    """Chat prompt a given post_id
    """

    post_id = request.args.get('post_id')
    analyze_post(post_id)
    return jsonify({'message': 'analyze_post endpoint'})

@app.route('/analyze_posts', methods=['GET'])
@jwt_required()
def analyze_posts_endpoint():
    """Chat prompt all post_ids
    """

    analyze_posts()
    return jsonify({'message': 'analyze_posts endpoint'})

def analyze_posts():
    """Chat prompt a post title + post body
    """

    logging.info('Analyzing Posts')
    post_ids = db_get_post_ids()
    if not post_ids:
        return

    for a_post_id in post_ids:
        logging.info('Analyzing Post ID %s', a_post_id)
        analyze_post(a_post_id)

def analyze_post(post_id):
    """Analyze text from Reddit Post
    """

    logging.info('Analyzing post ID %s', post_id)

    #TODO(fixme): handle updates to posts that may have occurred after they were
    #       added to the database. Currently, posts are stored in their
    #       original form as they were when they were collected.
    sql_query = f"""SELECT post_title, post_body, post_id
                    FROM post
                    WHERE post_id='{post_id}'
                    AND post_body NOT IN ('', '[removed]', '[deleted]');"""
    post_data =  get_select_query_results(sql_query)
    if not post_data:
        logging.warning('Post ID %s contains no body', post_id)
        return

    # post_title, post_body for ChatGPT
    text = post_data[0][0] + post_data[0][1]
    # post_id
    post_id = post_data[0][2]
    try:
        language = detect(text)
        # starting at ollama 0.1.24 and .25, it hangs on greek text
        if language not in ('en'):
            logging.warning('Skipping %s - langage detected %s', post_id, language)
            return
    except langdetect.lang_detect_exception.LangDetectException as e:
        logging.warning('Skipping %s - langage detected UNKNOWN %s', post_id, e)
    prompt = 'respond to this post title and post body: '

    for llm in LLMS:
        analyzed_obj, _ = asyncio.run(prompt_chat(llm, prompt + text, False))

        # jsonb document
        #  schema_version key added starting v2
        analysis_document = {
                            'schema_version' : '3',
                            'source' : 'reddit',
                            'category' : 'post',
                            'reference_id' : post_id,
                            'llm' : llm,
                            'analysis' : analyzed_obj['analysis']
                            }
        analysis_data = {
                        'timestamp': analyzed_obj['timestamp'],
                        'shasum_512' : analyzed_obj['shasum_512'],
                        'analysis_document' : json.dumps(analysis_document)
                        }
        insert_data_into_table('analysis_documents', analysis_data)

@app.route('/analyze_comment', methods=['GET'])
@jwt_required()
def analyze_comment_endpoint():
    """Chat prompt a given comment_id
    """

    comment_id = request.args.get('comment_id')
    analyze_comment(comment_id)
    return jsonify({'message': 'analyze_comment endpoint'})

@app.route('/analyze_comments', methods=['GET'])
@jwt_required()
def analyze_comments_endpoint():
    """Chat prompt all post_ids
    """

    analyze_comments()
    return jsonify({'message': 'analyze_comments endpoint'})

def analyze_comments():
    """Chat prompt a comment
    """

    logging.info('Analyzing Comments')
    comment_ids = db_get_comment_ids()
    if not comment_ids:
        logging.warning('No comments to analyze')
        return

    for a_comment_id in comment_ids:
        analyze_comment(a_comment_id)

def analyze_comment(comment_id):
    """Analyze text
    """

    logging.info('Analyzing comment ID %s', comment_id)

    sql_query = f"""SELECT comment_id, comment_body
                    FROM comment
                    WHERE comment_id='{comment_id}'
                    AND comment_body NOT IN ('', '[removed]', '[deleted]');"""
    comment_data =  get_select_query_results(sql_query)
    if not comment_data:
        logging.warning('Comment ID %s contains no body', comment_id)
        return

    # comment_body for ChatGPT
    text = comment_data[0][1]
    # comment_id
    comment_id = comment_data[0][0]
    try:
        language = detect(text)
        # starting at ollama 0.1.24 and .25, it hangs on greek text
        if language not in ('en'):
            logging.warning('Skipping %s - langage detected %s', comment_id, language)
            return
    except langdetect.lang_detect_exception.LangDetectException as e:
        logging.warning('Skipping %s - langage detected UNKNOWN %s', comment_id, e)

    prompt = 'respond to this comment: '

    for llm in LLMS:
        analyzed_obj, _ = asyncio.run(prompt_chat(llm, prompt + text, False))

        # jsonb document
        #  schema_version key added starting v2
        analysis_document = {
                            'schema_version' : '3',
                            'source' : 'reddit',
                            'category' : 'comment',
                            'reference_id' : comment_id,
                            'llm' : llm,
                            'analysis' : analyzed_obj['analysis']
                            }
        analysis_data = {
                        'timestamp': analyzed_obj['timestamp'],
                        'shasum_512' : analyzed_obj['shasum_512'],
                        'analysis_document' : json.dumps(analysis_document)
                        }
        insert_data_into_table('analysis_documents', analysis_data)

@app.route('/analyze_visit_notes', methods=['GET'])
@jwt_required()
def analyze_visit_notes_endpoint():
    """Analyze all OSCE format Visit Notes that exist in database
    """

    analyze_visit_notes()
    return jsonify({'message': 'analyze_visit_notes endpoint'})

def analyze_visit_notes():
    """Analyze all visit notes in the db
    """
    sql_query = """SELECT
                        patient_note_id
                   FROM 
                        patient_notes;
                """

    all_visit_notes = get_select_query_results2(sql_query)
    for a_visit_note_id in all_visit_notes:
        analyze_visit_note(a_visit_note_id['patient_note_id'])

@app.route('/analyze_visit_note', methods=['GET'])
@jwt_required()
def analyze_visit_note_endpoint():
    """Analyze OSCE format Visit Note that exists in the database
    """

    visit_note_id = request.args.get('visit_note_id')
    analyze_visit_note(visit_note_id)
    return jsonify({'message': 'analyze_visit_note endpoint'})

def analyze_visit_note(visit_note_id):
    """Analyze a specific visit note that exists in the database
    """

    sql_query = f"""SELECT
                        patient_id, patient_note_id, patient_note 
                   FROM 
                        patient_notes
                   WHERE patient_note_id = '{visit_note_id}';
                """

    visit_notes = get_select_query_results2(sql_query)

    for visit_note in visit_notes:
        patient_id = visit_note['patient_id']
        patient_note_id = visit_note['patient_note_id']

        # this note text is encrypted in the patient_notes table
        content = decrypt_text(visit_note['patient_note']['note'])

        prompt = """based on doctor patient visit note, where P is patient, and D is doctor, \
                  summarize the conversation into a single paragraph prompt, include patient's \
                  age and gender if stated, keep all the pertinent details: """
        summarized_obj, _ = asyncio.run(prompt_chat('deepseek-llm', prompt + content))

        # summary is created here, and then used for diagnostics, should be encrypted when
        #  before storing it in db
        osce_note_summarized = summarized_obj['analysis']
        prompt = 'Diagnose this patient: '

        # PII should always be encrypted
        for llm in MEDLLMS:
            analyzed_obj, encrypt_analysis = asyncio.run(
                                                         prompt_chat(
                                                                     llm,
                                                                     prompt +
                                                                     summarized_obj['analysis']
                                                                    )
                                                        )
            # decrypt for ICD/DPT codes processing only. this happens and should ONLY happen here
            recommended_diagnosis = decrypt_text(analyzed_obj['analysis'])
            patient_document_id = analyzed_obj['shasum_512']
            get_store_icd_cpt_codes(patient_id, patient_document_id, llm, recommended_diagnosis)
            recommended_diagnosis = analyzed_obj['analysis'] #originally encrypted

            if encrypt_analysis:
                osce_note_summarized = encrypt_text(summarized_obj['analysis']).decode('utf-8')
            else:
                logging.error('URGENT: Patient Data Encryption disabled! \
                              If spotted in Production logs, notify immediately!')

            patient_data_obj = {
                                'schema_version' : '3',
                                'llm' : llm,
                                'source' : 'healthcare',
                                'category' : 'patient',
                                'patient_id' : patient_id,
                                'patient_note_id' : patient_note_id,
                                'osce_note_summarized' : osce_note_summarized,
                                'analysis_document' : recommended_diagnosis 
                                }
            patient_analysis_data = {
                                        'timestamp' : analyzed_obj['timestamp'],
                                        'patient_document_id' : patient_document_id,
                                        'patient_id' : patient_id,
                                        'patient_note_id' : patient_note_id,
                                        'analysis_document' : json.dumps(patient_data_obj)
                                        }
            insert_data_into_table('patient_documents', patient_analysis_data)

def get_store_icd_cpt_codes(patient_id, patient_document_id, llm, analyzed_content):
    """Get icd and cpt codes for the diagnosis and store the two
        as JSON in the table
    """

    if llm != 'meditron':
        icd_prompt = 'List relevant ICD codes for the diagnosis: '
        cpt_prompt = 'List relevant CPT codes for the diagnosis: '
        prescription_prompt = 'What medication would be prescribed for the diagnosis: '

    if llm == 'meditron':
        icd_prompt = 'What are the relevant ICD codes for the diagnosis: '
        cpt_prompt = 'What are the relevant CPT codes for the diagnosis: '
        prescription_prompt = 'What medication would be prescribed for the diagnosis: '

    # do not encrypt
    icd_obj, _ = asyncio.run(prompt_chat(llm, icd_prompt + analyzed_content, False))

    # do not encrypt
    cpt_obj, _ = asyncio.run(prompt_chat(llm, cpt_prompt + analyzed_content, False))

    # do not encrypt
    prescription_obj, _ = asyncio.run(prompt_chat(llm, prescription_prompt + analyzed_content, False))

    codes_document = {
                      'icd' : {
                               'timestamp' : serialize_datetime(icd_obj['timestamp']),
                               'codes' : icd_obj['analysis']
                              },
                      'cpt' : { 
                               'timestamp' : serialize_datetime(cpt_obj['timestamp']),
                               'codes' : cpt_obj['analysis']
                              },
                      'prescriptions' : { 
                                         'timestamp' : serialize_datetime(cpt_obj['timestamp']),
                                         'prescriptions' : cpt_obj['analysis']
                                        }
                     }
    codes_data = {
                  'timestamp' : serialize_datetime(ts_int_to_dt_obj()),
                  'patient_id' : patient_id,
                  'patient_document_id' : patient_document_id,
                  'codes_document' : json.dumps(codes_document)
                 }
    insert_data_into_table('patient_codes', codes_data)

async def prompt_chat(llm,
                      content,
                      encrypt_analysis=CONFIG.getboolean('service',
                                                         'PATIENT_DATA_ENCRYPTION_ENABLED')
                     ):
    """Llama Chat Prompting and response
    """

    dt = ts_int_to_dt_obj()
    client = AsyncClient(host=CONFIG.get('service','OLLAMA_API_URL'))
    logging.info('Running for %s', llm)
    try:
        response = await client.chat(
                                        model=llm,
                                        stream=False,
                                        messages=[
                                                {
                                                    'role': 'user',
                                                    'content': content
                                                },
                                                ],
                                        options = {
                                                    'temperature' : 0
                                                }
                                        )

        # chatgpt analysis
        analysis = response['message']['content']
        analysis = sanitize_string(analysis)

        # this is for the analysis text only - the idea is to avoid
        #  duplicate text document, to allow indexing the column so
        #  to speed up search/lookups
        analysis_sha512 = hashlib.sha512(str.encode(analysis)).hexdigest()

        # see encryption.py module
        # encrypt text *** make sure that encryption key file is secure! ***

        if encrypt_analysis:
            analysis = encrypt_text(analysis).decode('utf-8')

        analyzed_obj = {
                        'timestamp' : dt,
                        'shasum_512' : analysis_sha512,
                        'analysis' : analysis
                        }

        return analyzed_obj, encrypt_analysis
    except (httpx.ReadError, httpx.ConnectError) as e:
        logging.error('%s',e.args[0])
        raise httpx.ConnectError('Unable to reach Ollama Server') from None

@app.route('/get_sub_post', methods=['GET'])
@jwt_required()
def get_post_endpoint():
    """Get submission post content for a given post id
    """

    post_id = request.args.get('post_id')
    get_sub_post(post_id)
    return jsonify({'message': 'get_sub_post endpoint'})

@app.route('/get_sub_posts', methods=['GET'])
@jwt_required()
def get_sub_posts_endpoint():
    """Get submission posts for a given subreddit
    """

    sub = request.args.get('sub')
    get_sub_posts(sub)
    return jsonify({'message': 'get_sub_posts endpoint'})

def get_sub_post(post_id):
    """Get a submission post
    """

    logging.info('Getting post id %s', post_id)

    post = REDDIT.submission(post_id)
    post_data = get_post_details(post)
    insert_data_into_table('post', post_data)
    get_post_comments(post)

def get_sub_posts(sub):
    """Get all posts for a given sub
    """

    logging.info('Getting posts in subreddit %s', sub)
    try:
        posts = REDDIT.subreddit(sub).hot(limit=None)
        new_post_ids = get_new_data_ids('post', 'post_id', posts)
        counter = 0
        for post_id in new_post_ids:
            get_sub_post(post_id)
            counter = sleep_to_avoid_429(counter)
    except AttributeError as e:
        # store this for later inspection
        error_data = {
                      'item_id': sub,
                      'item_type': 'GET SUB POSTS',
                      'error': e.args[0]
                     }
        insert_data_into_table('errors', error_data)
        logging.warning('GET SUB POSTS %s %s', sub, e.args[0])

def get_post_comments(post_obj):
    """Get all comments made to a submission post
    """

    logging.info('Getting comments for post %s', post_obj.id)

    for comment in post_obj.comments:
        comment_data = get_comment_details(comment)
        insert_data_into_table('comment', comment_data)

def get_post_details(post):
    """Get details for a submission post
    """

    post_author = post.author.name if post.author else None

    if post_author != 'AutoModerator':
        process_author(post_author)

    post_data = {
                 'subreddit': post.subreddit.display_name,
                 'post_id': post.id,
                 'post_author': post_author,
                 'post_title': post.title,
                 'post_body': post.selftext,
                 'post_created_utc': int(post.created_utc),
                 'is_post_oc': post.is_original_content,
                 'is_post_video': post.is_video,
                 'post_upvote_count': post.ups,
                 'post_downvote_count': post.downs,
                 'subreddit_members': post.subreddit_subscribers
                }
    return post_data

def get_comment_details(comment):
    """Get comment details
    """

    comment_author = comment.author.name if comment.author else None
    comment_submitter = comment.is_submitter if hasattr(comment, 'is_submitter') else None
    comment_edited = str(int(comment.edited)) if comment.edited else False

    if comment_author:
        process_author(comment_author)

    comment_data = {
                    'comment_id': comment.id,
                    'comment_author': comment_author,
                    'is_comment_submitter': comment_submitter,
                    'is_comment_edited': comment_edited,
                    'comment_created_utc': int(comment.created_utc),
                    'comment_body': comment.body,
                    'post_id': comment.submission.id,
                    'subreddit': comment.subreddit.display_name
                   }
    return comment_data

@app.route('/get_author_comments', methods=['GET'])
@jwt_required()
def get_author_comments_endpoint():
    """Get all comments for a given author
    """

    author = request.args.get('author')
    get_author_comments(author)
    return jsonify({'message': 'get_author_comments endpoint'})

@app.route('/get_authors_comments', methods=['GET'])
@jwt_required()
def get_authors_comments_endpoint():
    """Get all comments for each author from a list of author in db
    """

    get_authors_comments()
    return jsonify({'message': 'get_authors_comments endpoint'})

def process_author(author_name):
    """Process author information.
    """

    logging.info('Processing Author %s', author_name)

    author_data = {}
    try:
        author = REDDIT.redditor(author_name)
        if author.name != 'AutoModerator':
            author_data = {
                           'author_id': author.id,
                           'author_name': author.name,
                           'author_created_utc': int(author.created_utc),
                          }
            insert_data_into_table('author', author_data)
    except (AttributeError, TypeError, exceptions.NotFound) as e:
        # store this for later inspection
        error_data = {
                      'item_id': author_name,
                      'item_type': 'AUTHOR',
                      'error': e.args[0]
                     }
        insert_data_into_table('errors', error_data)
        logging.warning('AUTHOR %s %s', author_name, e.args[0])

def get_author(anauthor):
    """Get author info of a comment or a submission
    """

    process_author(anauthor)
    get_author_comments(anauthor)

def process_comment(comment):
    """Process a single comment
    """

    comment_body = comment.body

    if comment_body not in ('[removed]', '[deleted]') and comment.author.name != 'AutoModerator':
        comment_data = get_comment_details(comment)
        insert_data_into_table('comment', comment_data)
        orig_post = REDDIT.submission(comment_data['post_id'])
        post_data = get_post_details(orig_post)
        insert_data_into_table('post', post_data)

    if comment_body in ('[removed]', '[deleted]'): #removed or deleted comments
        comment_data = get_comment_details(comment)
        insert_data_into_table('comment', comment_data)

def get_authors_comments():
    """Get comments and posts for authors listed in the author table, 
        insert data into db
    """

    authors = db_get_authors()
    if not authors:
        logging.warning('db_get_authors(): No authors found in DB')
        return

    counter = 0
    for an_author in authors:
        try:
            REDDIT.redditor(an_author)
            get_author_comments(an_author)
            counter = sleep_to_avoid_429(counter)
        except exceptions.NotFound as e:
            # store this for later inspection
            error_data = {
                          'item_id': an_author,
                          'item_type': 'REDDITOR DELETED',
                          'error': e.args[0]
                         }
            insert_data_into_table('errors', error_data)
            logging.warning('AUTHOR DELETED %s %s', an_author, e.args[0])


def get_author_comments(author):
    """Get author comments, author posts, insert data into db
    """

    logging.info('Getting comments for %s', author)

    try:
        redditor = REDDIT.redditor(author)
        comments = redditor.comments.hot(limit=None)
        author_comments = get_new_data_ids('comment', 'comment_id', comments)
        if not author_comments:
            logging.info('%s has no new comments', author)
            return

        counter = 0
        if author_comments:
            num_comments = len(author_comments)
            logging.info('%s %s new comments', author, num_comments)
            for comment_id in author_comments:
                comment = REDDIT.comment(comment_id)
                process_comment(comment)
                counter = sleep_to_avoid_429(counter)

    except AttributeError as e:
        # store this for later inspection
        error_data = {
                      'item_id': comment_id,
                      'item_type': 'COMMENT',
                      'error': e.args[0]
                     }
        insert_data_into_table('errors', error_data)
        logging.warning('AUTHOR COMMENT %s %s', comment_id, e.args[0])

    # when author has no comments available - either author has been removed or blocked
    except exceptions.Forbidden as e:
        # store this for later inspection
        error_data = {
                      'item_id': 'COMMENT_ID_NOT_AVAILABLE',
                      'item_type': 'COMMENT',
                      'error': e.args[0]
                     }
        insert_data_into_table('errors', error_data)
        logging.warning('AUTHOR COMMENT %s %s', author, e.args[0])

@app.route('/join_new_subs', methods=['GET'])
@jwt_required()
def join_new_subs_endpoint():
    """Join all new subs from post database
    """

    join_new_subs()
    return jsonify({'message': 'join_new_subs_endpoint endpoint'})

def join_new_subs():
    """Join newly discovered subreddits
    """

    logging.info('Joining New Subs')
    new_subs = []
    dt = unix_ts_str()

    # get new subs
    sql_query = """select subreddit from post where subreddit not in \
                (select subreddit from subscription) group by subreddit;"""
    new_sub_rows = get_select_query_results(sql_query)
    if not new_sub_rows:
        logging.info('No new subreddits to join')
        return

    for a_row in new_sub_rows:
        if not a_row[0].startswith('u_'):
            new_subs.append(a_row[0])

    if new_subs:
        for new_sub in new_subs:
            logging.info('Joining new sub %s', new_sub)
            try:
                REDDIT.subreddit(new_sub).subscribe()
                sub_data = {
                            'datetimesubscribed' : dt,
                            'subreddit' : new_sub
                           }
                insert_data_into_table('subscription', sub_data)
            except (exceptions.Forbidden, exceptions.NotFound) as e:
                # store this for later inspection
                error_data = {
                              'item_id': new_sub,
                              'item_type': 'SUBREDDIT',
                              'error': e.args[0]
                             }
                insert_data_into_table('errors', error_data)
                logging.error('Unable to join %s - %s', new_sub, e.args[0])

@app.route('/get_and_analyze_post', methods=['GET'])
@jwt_required()
def get_and_analyze_post_endpoint():
    """Fetch post from Reddit, then Chat prompt a given post_id
    """

    post_id = request.args.get('post_id')
    get_and_analyze_post(post_id)
    return jsonify({'message': 'get_and_analyze_post endpoint'})

def get_and_analyze_post(post_id):
    """If post does not exist, fetch it, then analyze it
    """

    post_ids = db_get_post_ids()
    if not post_ids or post_id not in post_ids:
        logging.warning('Post ID %s not found in local database', post_id)
        get_sub_post(post_id)
        analyze_post(post_id)
    else:
        logging.info('Post ID %s has already been analyzed', post_id)

@app.route('/get_and_analyze_comment', methods=['GET'])
@jwt_required()
def get_and_analyze_comment_endpoint():
    """Fetch comment from Reddit, then Chat prompt a given comment_id
    """

    comment_id = request.args.get('comment_id')
    get_and_analyze_comment(comment_id)
    return jsonify({'message': 'get_and_analyze_comment endpoint'})

def get_comment(comment_id):
    """Get a Reddit comment
    """

    logging.info('Getting comment id %s', comment_id)

    comment = REDDIT.comment(comment_id)
    comment_data = get_comment_details(comment)
    insert_data_into_table('comment', comment_data)

def get_and_analyze_comment(comment_id):
    """If post does not exist, fetch it, then analyze it
    """

    comment_ids = db_get_comment_ids()
    if not comment_ids or comment_id not in comment_ids:
        logging.warning('Comment ID %s not found in local database', comment_id)
        get_comment(comment_id)
        analyze_comment(comment_id)
    else:
        logging.info('Comment ID %s has already been analyzed', comment_id)

def reply_post(post_id):
    """WIP"""
    # filter out non answers
    sql_query = f"""select
                        analysis_document ->> 'post_id' as post_id,
                        analysis_document ->> 'analysis' as analysis
                    from
                        analysis_documents
                    where
                        analysis_document ->> 'post_id' = '{post_id}'
                        and analysis_document ->> 'analysis' not like '%therefore I cannot answer this question.%';
                 """

    analyzed_data = get_select_query_results(sql_query)

    if analyzed_data:
        a_post = REDDIT.submission('1b0yadp')
        a_post.reply()

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO) # init logging
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    # non-production WSGI settings:
    #  port 5000, listen to local ip address, use ssl
    # in production we use gunicorn
    app.run(port=5000,
            host='0.0.0.0',
            ssl_context=('cert.pem', 'key.pem'),
            debug=False) # not for production
