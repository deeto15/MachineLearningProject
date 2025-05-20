pip install numpy==1.26.4,spacy,transformers==4.47.1,datasets,seqeval,nltk,torch,pandas,sklearn,pathlib,accelerate==1.2.1,tiingo==0.16.1,
pip install psycopg2-binary

You'll need to download the submissions file from google drive and put it directly in your downloads folder
To train it, youll need to run the classifier file in NER_classifier to train that part, then run the BERT_classifier in Binary_Classifier to train the second part, then just run main to actually run the script 

order of bug fixes
1. retrain model with negatives, it's main area of missing them is comments that it gets trigger happy on what a stock name is
2. missing sanitizations in formatter.py
3. double check live_scraper, when it rescrapes a post, does it insert the comments into the db that are good? since it may have different scores, it may technically be different. need to check what determines a duplicate comment, only comment_id? or all fields identical?
4. rework past_scraper.py
    4a. append posts to comments as fake comments
    4b. do i even need to store posts for old posts? I don't really think so since i never rescan them again. maybe drop old posts from the db entirely. would mean reworking the foreign key somehow between post and comments
    4c. if you stop midway through a comments file, progress is not saved

optimizations
1. find a way to avoid tiingo api limits
2. retrain dual head bert model to save inference
3. sam's kafka setup
