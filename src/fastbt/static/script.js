console.log("Hello world");

var app = new Vue({
    el: "#app",
    data: {
        columns_list: ["open", "high", "low", "close", "volume"],
        operators: ["+", "-"],
        indicator_list: ["SMA", "EMA"],
        col_type: "lag",
        col_name: null,
        columns: [],
        conditions: [],
        formula: null,
        isIndicator: false,
        isFormula: false,
        isRolling: false
    },
    methods: {
        setStatus(text) {
            // Set the status of the variable
            switch (text) {
                case "indicator":
                    this.isIndicator = true;
                    this.isFormula = false;
                    this.isRolling = false;
                    break;
                case "rolling":
                    this.isRolling = true;
                    this.isFormula = false;
                    this.isIndicator = false;
                    break;
                case "formula":
                    this.isFormula = true;
                    this.isRolling = false;
                    this.isIndicator = false;
                    break;
            }
        },
        evalFormula() {
            // evaluate formula
            if (this.col_name == null) {
                return false;
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
        addColumn(text) {
            let mapper = {
                lag: "L",
                percent_change: "P",
                formula: "F",
                indicator: "I",
                rolling: "R"
            };
            let col_type = mapper[text];
            if (col_type == "F") {
                let val = this.evalFormula();
                if (val) {
                    console.log(val);
                    this.columns.push(val);
                }
                this.formula = null;
                this.col_name = null;
            }
        }
    }
});
