pip install numpy==1.26.4,spacy,transformers==4.47.1,datasets,seqeval,nltk,torch,pandas,sklearn,pathlib,accelerate==1.2.1,tiingo==0.16.1,
pip install psycopg2-binary

You'll need to download the submissions file from google drive and put it directly in your downloads folder
To train it, youll need to run the classifier file in NER_classifier to train that part, then run the BERT_classifier in Binary_Classifier to train the second part, then just run main to actually run the script 

order of bug fixes
1. retrain model with negatives, it's main area of missing them is comments that it gets trigger happy on what a stock name is
    1a. scrape all stock names that are invalid from the stock harvester and feed in as bad data, maybe need to figure out api limits so i can mass scrape
    
2. rework past_scraper.py
    2a. append posts to comments as fake comments
    2b. do i even need to store posts for old posts? I don't really think so since i never rescan them again. maybe drop old posts from the db entirely. would mean reworking the foreign key somehow between post and comments
    2c. if you stop midway through a comments file, progress is not saved

optimizations
1. find a way to avoid tiingo api limits
2. retrain dual head bert model to save inference
3. sam's kafka setup
