import { ref, reactive, watch } from 'vue';

export const default_material_record = reactive({
    id: 0,
    order_num: '',                  //訂單編號
    material_num: '',               //物料編號
    req_qty: 0,                     //需求數量
    delivery_qty: 0,                //備料數量
    total_delivery_qty: 0,          //應備數量
    input_disable: false,
    date: '',                       //(建立日期)
    delivery_date:'',               //交期
    shortage_note: '',              //缺料註記 '元件缺料'
    comment: '',                    //說明
    isTakeOk: false,
    isLackMaterial: 99,
    isBatchFeeding:  99,
    isShow: false,
    whichStation: 1,
    show1_ok: '1',
    show2_ok: '0',
    show3_ok: '0',
  });

