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
        "https://archives.nseindia.com/archives/equities/bhavcopy/pr/PR{date}.zip",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
    "old_derivatives": (
        "https://archives.nseindia.com/content/historical/DERIVATIVES/{year}/{month}/fo{date}bhav.csv.zip",
        lambda x: {
            "year": x.year,
            "month": x.strftime("%b").upper(),
            "date": x.strftime("%d%b%Y").upper(),
        },
    ),
    "derivatives": (
        "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date}_F_0000.csv.zip",
        lambda x: {
            "date": x.strftime("%Y%m%d"),
        },
    ),
    "combineoi_deleq": (
        "https://nsearchives.nseindia.com/archives/nsccl/mwpl/combineoi_deleq_{date}.csv",
        lambda x: {
            "date": x.strftime("%d%m%Y"),
        },
    ),
    "bhav_sec": (
        "https://archives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "indices": (
        "https://archives.nseindia.com/content/indices/ind_close_all_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "top10marketcap": (
        "https://archives.nseindia.com/content/indices/top10nifty50_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
    "fii_stats": (
        "https://archives.nseindia.com/content/fo/fii_stats_{date}.xls",
        lambda x: {"date": x.strftime("%d-%b-%Y")},
    ),
    "fno_participant": (
        "https://archives.nseindia.com/content/nsccl/fao_participant_vol_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "fno_category": (
        "https://archives.nseindia.com/archives/fo/cat/fo_cat_turnover_{date}.xls",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
    "fno_oi_participant": (
        "https://archives.nseindia.com/content/nsccl/fao_participant_oi_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "equity_info": (
        "https://www.nseindia.com/api/quote-equity?symbol={symbol}",
        lambda x: {"symbol": x.upper()},
    ),
    "trade_info": (
        "https://www.nseindia.com/api/quote-equity?symbol={symbol}&section=trade_info",
        lambda x: {"symbol": x.upper()},
    ),
    "ipo_eq": (
        "https://www.nseindia.com/api/ipo-detail?symbol={symbol}&series=EQ",
        lambda x: {"symbol": x.upper()},
    ),
    "hist_data": (
        "https://www.nseindia.com/api/historical/cm/equity?symbol={symbol}",
        lambda x: {"symbol": x.upper()},
    ),
    "nse_oi": (
        "https://archives.nseindia.com/archives/nsccl/mwpl/nseoi_{date}.zip",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "oi_cli_limit": (
        "https://archives.nseindia.com/content/nsccl/oi_cli_limit_{date}.lst",
        lambda x: {"date": x.strftime("%d-%b-%Y").upper()},
    ),
    "fo": (
        "https://archives.nseindia.com/archives/fo/mkt/fo{date}.zip",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "fo_volt": (
        "https://archives.nseindia.com/archives/nsccl/volt/FOVOLT_{date}.csv",
        lambda x: {"date": x.strftime("%d%m%Y")},
    ),
    "mrg_trading": (
        "https://nsearchives.nseindia.com/content/equities/mrg_trading_{date}.zip",
        lambda x: {"date": x.strftime("%d%m%y")},
    ),
}
