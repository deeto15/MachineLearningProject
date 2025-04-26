pip install spacy,transformers,datasets,seqeval,nltk,torch,pandas,sklearn,pathlib
You'll need to download the submissions file from google drive and put it directly in your downloads folder
To train it, youll need to run the classifier file in NER_classifier to train that part, then run the BERT_classifier in Binary_Classifier to train the second part, then just run main to actually run the script 
#new model grabs roughly 2.5% of the comments out of the dataset, was previously 1% with the old model and sub 1% before that