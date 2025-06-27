from tables import AbnormalCause, Session

import pymysql
from sqlalchemy import exc


# --------------------------
insert_count = 0

s = Session()

new_cause = AbnormalCause(number='M00001', message='備料區來料數量不對')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M00002', message='組裝區來料數量不對')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01001', message='混料')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01002', message='散爪')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01003', message='掉爪')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01004', message='撞傷')
s.add(new_cause)
new_cause = AbnormalCause(number='M01005', message='生鏽')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01006', message='蛀孔')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01007', message='染黑不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01008', message='鍍鈦不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01010', message='端面不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01011', message='外觀不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01012', message='牙形不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01013', message='牙紋不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01014', message='斜套後端不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01015', message='後套同心不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01016', message='90°平行線不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01017', message='固定環染黑不良')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01018', message='斜套釘孔')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01019', message='拆解損毀')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01020', message='壓配損毀')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01021', message='組裝損毀')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01022', message='鎖緊卡死')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01023', message='本體爪溝緊')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01024', message='本體高度過高')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01025', message='三爪90°未磨')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01026', message='本體外徑過大')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01027', message='斜套內孔生鏽')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01028', message='端面刮傷嚴重')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01029', message='本體端面生鏽')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01030', message='轉牙轉不下去')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01031', message='爪軸GO下不去')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01032', message='驗不起來(對點)')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01033', message='驗不起來(高點不同)')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01034', message='驗不起來(弧度不良)')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01035', message='驗不起來(偏擺過大)')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01036', message='驗不起來(高點不同，對點)')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01037', message='驗不起來(高點不同，弧度不良)')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01038', message='卡死')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01039', message='作動不順暢')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01040', message='固定環卡砂')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01041', message='內孔偏擺過大')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01042', message='組裝後偏擺過大')
s.add(new_cause)
insert_count +=1

new_cause = AbnormalCause(number='M01043', message='M8攻牙同心不良')
s.add(new_cause)
insert_count +=1

try:
  s.commit()
  #print("AbnormalCause data committed successfully")
except pymysql.err.IntegrityError as e:
  print(f"IntegrityError: {e}")
  s.rollback()
except exc.IntegrityError as e:
  print(f"SQLAlchemy IntegrityError: {e}")
  s.rollback()
except Exception as e:
  print(f"Exception: {e}")
  s.rollback()

# --------------------------

s.close()
_str_insert_count = str(insert_count)
print(f"insert {_str_insert_count} AbnormalCause data is ok...")