pip install numpy==1.26.4,spacy,transformers==4.47.1,datasets,seqeval,nltk,torch,pandas,sklearn,pathlib,accelerate==1.2.1
You'll need to download the submissions file from google drive and put it directly in your downloads folder
To train it, youll need to run the classifier file in NER_classifier to train that part, then run the BERT_classifier in Binary_Classifier to train the second part, then just run main to actually run the script 

So things that need done that aren't super important are retraining the head into a dual head single bert model, optimizing code for batch processing (will probably be easier to just do it all at once when i get the scrapers and stuff running), and maybe retraining the model once i get some more training data.

Things that need done but can't be done until i get other parts of the model are the validation script (checking a stock name to see if uppercasing it makes it valid, if not comparing it against the real price and seeing if its within a reasonable range)

i just dont really know what i want to do or where i want to start next, i guess the scraper since its already mostly done?