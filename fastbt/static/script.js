console.log("Hello world");

var app = new Vue({
  el: "#app",
  data: {
    start: "2018-06-01",
    end: "2018-06-30",
    capital: 100000,
    leverage: 1,
    commission: 0,
    slippage: 0,
    selector: null,
    columns_list: [
      'open', 'high', 'low', 'close', 'volume'
    ],
    indicator_list: [
      'SMA', 'EMA'

    ],
    columns: [],
    temp_column: '',
    conditions: [],
    temp: null,
    col: null,
    param1: 0,
    col_name: null
  },
  methods: {
    clickMe(text) {
      alert(text);
    },
    addToText(text) {
      this.temp_column = this.temp_column + text
    },
    addToList() {
      this.collect.push({
        num: this.temp
      });
      this.result = JSON.stringify(this.collect);
      console.log("LOGGED", JSON.stringify(this.collect));
      this.temp = null;
    },
    addColumn() {
      this.columns.push(
        JSON.stringify({
          func: this.col,
          param: this.param1,
          col_name: this.col_name
        })
      );
      this.col = this.param1 = this.col_name = null;
    }
  }
});