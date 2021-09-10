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
}
