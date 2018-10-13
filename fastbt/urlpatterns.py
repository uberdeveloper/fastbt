file_patterns = {
    'bhav': (
        'https://www.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{date}bhav.csv.zip',
        lambda x: {
            'year': x.year,
            'month': x.strftime('%b').upper(),
            'date': x.strftime('%d%b%Y').upper()            
        }
    ),
    
    'sec_del': (
        'https://www.nseindia.com/archives/equities/mto/MTO_{date}.DAT',
        lambda x: {
            'date': x.strftime('%d%m%Y')
        }
    ),
    
    'bhav_pr': (
        'https://www.nseindia.com/archives/equities/bhavcopy/pr/PR{date}.zip',
        lambda x: {
            'date': x.strftime('%d%m%Y')
        }
    ),
    
    'derivatives': (
        'https://www.nseindia.com/content/historical/DERIVATIVES/{year}/{month}/fo{date}bhav.csv.zip',
        lambda x: {
            'year': x.year,
            'month': x.strftime('%b').upper(),
            'date': x.strftime('%d%b%Y').upper()           
        }
    )
}

