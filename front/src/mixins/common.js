import axios from 'axios'

export function myMixin() {
  function initAxios() {
    let _host = window.location.host;
    _host = _host.slice(0, _host.lastIndexOf(":"));
    let _protocol = window.location.protocol;
    axios.defaults.baseURL = _protocol + "//"+ _host + ':8082';             //for backend server
    axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';   //確認request是否為XHR(XML Http Request)或者是正常的请求
  }

  return {
    initAxios,
  };
}
