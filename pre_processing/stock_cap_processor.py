#i had to find a way to get all stock ticker symbols and i didnt want to do it manually so i just bought them
import pandas as pd
#we are also adding a '$' in front of one or two letter stocks, so that some one starting a sentence with an all caps wont get flagged

def filter_stocks():
    df = pd.read_csv("stocks.csv")
    df['Symbol'] = df['Symbol'].astype(str)
    df.loc[df['Symbol'].str.len() <= 2, 'Symbol'] = '$' + df.loc[df['Symbol'].str.len() <= 2, 'Symbol']
    df_etfs = filter_etfs()
    combined = pd.concat([df['Symbol'], df_etfs], ignore_index=True)
    combined = combined.sort_values(key=lambda x: x.str.len(), ascending=False)
    return combined.values
    
def filter_etfs():
    df = pd.read_csv("etfs.csv")
    return df['Symbol']
