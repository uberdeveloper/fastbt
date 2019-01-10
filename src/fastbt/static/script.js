console.log("Hello world");
/*
Interface for python backtest
Columns are converted into their respective counterparts 
in DataSource
*/
var app = new Vue({
    el: "#app",
    data: {
        columns_list: ["open", "high", "low", "close", "volume"],
        function_list: [
            "count",
            "sum",
            "mean",
            "max",
            "min",
            "var",
            "std",
            "zscore"
        ],
        operators: ["+", "-", "*", "/", "(", ")", ">", "<", "==",
            ">=", "<=", "<>"
        ],
        indicator_list: ["SMA", "EMA", 'WMA', 'DEMA', 'TEMA', 'TRIMA',
            'MOM', 'ADX', 'ATR', 'CCI', 'WILLR', 'RSI', 'CCI',
        ],
        col_type: "lag",
        col_name: null,
        col_on: "close",
        columns: [],
        conditions: [],
        // column definitions
        period: 1,
        formula: null,
        lag: null,
        indicator: null,
        func: "mean",
        condition: '',
        // Status
        isLag: true,
        isPercentChange: false,
        isIndicator: false,
        isFormula: false,
        isRolling: false,
        mapper: {
            lag: "L",
            percent_change: "P",
            formula: "F",
            indicator: "I",
            rolling: "R"
        }
    },
    methods: {
        setStatus(text) {
            /* 
            Set the status of the given text to true
            and the others to false since only one
            of them could be active at a time
            */
            this.isLag = false;
            this.isPercentChange = false;
            this.isFormula = false;
            this.isRolling = false;
            this.isIndicator = false;
            switch (text) {
                case "lag":
                    this.isLag = true;
                    break;
                case "percent_change":
                    this.isPercentChange = true;
                    break;
                case "formula":
                    this.isFormula = true;
                    break;
                case "rolling":
                    this.isRolling = true;
                    break;
                case "indicator":
                    this.isIndicator = true;
                    break;
            }
        },
        clear() {
            // clear preset values from inputs
            this.formula = null;
            this.col_name = null;
            this.indicator = null;
            this.period = null;
        },
        evalLag() {
            // evaluate Lag parameter
            if (this.col_name == null) {
                this.col_name = "auto";
            } else {
                this.columns_list.push(this.col_name)
            }
            if (this.period == null) {
                return false;
            }
            return {
                L: {
                    period: this.period,
                    col_name: this.col_name,
                    on: this.col_on
                }
            };
        },
        evalPercentChange() {
            // evaluate percentage change
            if (this.col_name == null) {
                this.col_name = "auto";
            } else {
                this.columns_list.push(this.col_name)
            }
            if (this.period == null || this.lag == 0 || this.period == 0) {
                return false;
            }
            let P = {
                P: {
                    on: this.col_on,
                    period: this.period,
                    col_name: this.col_name
                }
            };
            // TO DO: Bug to fix for negative lag values
            if (this.lag == true) {
                P.P.lag = this.lag;
            }
            return P;
        },
        evalRolling() {
            // evaluate Rolling Window function
            if (this.col_name == null) {
                this.col_name = "auto";
            } else {
                this.columns_list.push(this.col_name)
            }
            if (this.period == null || this.lag == 0 || this.period == 0) {
                return false;
            }
            let R = {
                R: {
                    on: this.col_on,
                    window: this.period,
                    col_name: this.col_name,
                    function: this.func
                }
            };
            // TO DO: Bug to fix for negative lag values
            if (this.lag == true) {
                R.R.lag = this.lag;
            }
            return R;
        },
        evalFormula() {
            // evaluate formula
            if (this.col_name == null) {
                return false;
            } else {
                this.columns_list.push(this.col_name)
            }
            if (this.formula == null) {
                return false;
            }
            return {
                F: {
                    formula: this.formula,
                    col_name: this.col_name
                }
            };
        },
        evalIndicator() {
            // evaluate Indicator
            if (this.col_name == null) {
                this.col_name = 'auto'
            } else {
                this.columns_list.push(this.col_name)
            }
            if (this.period == null || this.lag == 0 || this.period == 0) {
                return false;
            }
            if (this.indicator == null) {
                return false;
            }
            let I = {
                I: {
                    indicator: this.indicator,
                    period: this.period,
                    col_name: this.col_name
                }
            };
            // TO DO: Bug to fix for negative lag values
            if (this.lag == true) {
                I.I.lag = this.lag;
            }
            return I;
        },
        addColumn(text) {
            let col_type = this.mapper[text];
            let val = null;
            if (col_type == "L") {
                val = this.evalLag();
            } else if (col_type == "P") {
                val = this.evalPercentChange();
            } else if (col_type == "F") {
                val = this.evalFormula();
            } else if (col_type == "R") {
                val = this.evalRolling();
            } else if (col_type == "I") {
                val = this.evalIndicator()
            }
            if (val) {
                console.log(val);
                this.columns.push(val);
            }
            this.clear();
        },
        extendCondition(text) {
            this.condition = this.condition + text
        },
        addCondition() {
            this.conditions.push(this.condition)
            this.condition = ''
        }
    }
});
