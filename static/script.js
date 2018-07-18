console.log("Hello world");

var app = new Vue({
  el: "#app",
  data: {
    message: "Hi!",
    first: "Tech",
    start: "2018-06-01",
    end: "2018-06-30",
    collect: [{ num: 4 }, { num: 7 }],
    columns: [],
    conditions: [],
    temp: null,
    col: null,
    param1: 0,
    col_name: null
  },
  methods: {
    clickMe() {
      alert("Hello");
    },
    addToList() {
      this.collect.push({ num: this.temp });
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
