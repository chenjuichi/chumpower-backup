// constructor
function Calendar(myEdit, myValue, myIndex, myClick) {
  this.myEdit = myEdit;
  this.myValue = myValue;
  this.myIndex = myIndex;
  this.myClick = myClick;
}

Calendar.prototype.form = function() {
  console.log('Calendar.prototype: ' + 'edit: ' + this.myEdit + ', value: ' + this.myValue + ', index: ' + this.myIndex + ', click: ' + this.myClick);

  //新增
  if (this.myEdit == '' && this.myValue == '' && this.myIndex == -1) {
    //console.log("con 2...");
    this.myValue=(new Date(Date.now() - (new Date()).getTimezoneOffset() * 60000)).toISOString().substr(0, 10);
    //console.log("con 21...", this.myValue);

    let yy_value=this.myValue.substring(0, 4);
    let mmdd_value=this.myValue.substring(5, this.myValue.length);
    mmdd_value=mmdd_value.replace('-','/');
    let b = parseInt(yy_value);
    b = b - 1911;
    yy_value = b.toString()
    this.myEdit = yy_value + '/' + mmdd_value;
    this.myValue='';
    return;
  }

  if (this.clickMenu) {
    console.log("con 3...");

    let yy_value = this.myValue.substring(0, 4);
    let mmdd_value = this.myValue.substring(5, this.myValue.length);
    mmdd_value = mmdd_value.replace('-','/');
    let b = parseInt(yy_value);
    b = b - 1911;
    yy_value = b.toString()
    this.myEdit = yy_value + '/' + mmdd_value;
    this.myValue = '';
    this.clickMenu = false;
    return;
  }

  if (this.myEdit != '' && this.myValue == '') {
    console.log("con 4...",this.myEdit, this.myValue);
    return;
  }
}

export {Calendar}
