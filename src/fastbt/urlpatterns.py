file_patterns = {
    "bhav": (
        "https://archives.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{date}bhav.csv.zip",
        lambda x: {
            "year": x.year,
            "month": x.strftime("%b").upper(),
            "date": x.strftime("%d%b%Y").upper(),
        },
    ),
    "sec_del": (
        "https://archives.nseindia.com/archives/equities/mto/MTO_{date}.DAT",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "bhav_pr": (
        "https://www.nseindia.com/archives/equities/bhavcopy/pr/PR{date}.zip",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "derivatives": (
        "https://www.nseindia.com/content/historical/DERIVATIVES/{year}/{month}/fo{date}bhav.csv.zip",
        lambda x: {
            "year": x.year,
            "month": x.strftime("%b").upper(),
            "date": x.strftime("%d%b%Y").upper(),
        },
    ),
    "bhav_sec": (
        "https://archives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "derivatives_zip": (
        "https://www1.nseindia.com/archives/fo/bhav/fo{date}.zip",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
    "indices": (
        "https://www1.nseindia.com/content/indices/ind_close_all_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "top10marketcap": (
        "https://www1.nseindia.com/content/indices/top10nifty50_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
    "fii_stats": (
        "https://www1.nseindia.com/content/fo/fii_stats_{date}.xls",
        lambda x: {"date": x.strftime("%d-%b-%Y")},
    ),
    "fno_participant": (
        "https://www1.nseindia.com/content/nsccl/fao_participant_vol_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "fno_category": (
        "https://www1.nseindia.com/archives/fo/cat/fo_cat_turnover_{date}.xls",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
    "fno_oi_participant": (
        "https://www1.nseindia.com/content/nsccl/fao_participant_oi_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "equity_info": (
        "https://www.nseindia.com/api/quote-equity?symbol={symbol}",
        lambda x: {"symbol": x},
    ),
    "trade_info": (
        "https://www.nseindia.com/api/quote-equity?symbol={symbol}&section=trade_info",
        lambda x: {"symbol": x},
    ),
    "ipo_eq": (
        "https://www.nseindia.com/api/ipo-detail?symbol={symbol}&series=EQ",
        lambda x: {"symbol": x},
    ),
    "ipo_bid": (
        "https://www.nseindia.com/api/ipo-bid-details?symbol={symbol}",
        lambda x: {"symbol": x},
    ),
}
