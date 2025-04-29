from flask import Blueprint, jsonify, request
from sqlalchemy import func

from database.tables import User, Session

import pymysql
from sqlalchemy import exc

deleteTable = Blueprint('deleteTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------

@deleteTable.route("/removeUser", methods=['POST'])
def remove_user():
    print("removeUser....")

    request_data = request.get_json()
    userID = request_data['ID']
    print("userID", userID, type(userID))
    s = Session()
    s.query(User).filter(User.emp_id == userID).update({'isRemoved': False})
    #s.commit()
    try:
      s.commit()
      print("Set data committed successfully")
    except pymysql.err.IntegrityError as e:
      print(f"IntegrityError: {e}")
      s.rollback()
    except exc.IntegrityError as e:
      print(f"SQLAlchemy IntegrityError: {e}")
      s.rollback()
    except Exception as e:
      print(f"Exception: {e}")
      s.rollback()

    s.close()

    return jsonify({
      'status': True,
    })

