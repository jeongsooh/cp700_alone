import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

JSON_FILE = 'shared_data.json'
ID_TAGS_KEY = 'registered_id_tags'
CHARGERS_KEY = 'registered_chargers'

class JsonConfigManager:
    """
    JSON 파일을 읽고 쓰며, OCPP 공유 데이터를 관리하는 클래스.
    """
    def __init__(self, filename: str):
        self.filename = filename

    def load_data(self) -> Dict[str, Any]:
        """JSON 파일에서 모든 데이터를 읽어 딕셔너리로 반환합니다."""
        if not os.path.exists(self.filename):
            print(f"Error: JSON file '{self.filename}' not found. Returning empty dictionary.")
            return {}
            
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON file: {e}")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred while reading the file: {e}")
            return {}

    def save_data(self, data: Dict[str, Any]):
        """주어진 딕셔너리 데이터를 JSON 파일에 저장합니다."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                # indent=4를 사용하여 파일에 저장 시 가독성을 높입니다.
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Success: JSON file '{self.filename}' updated.")
        except Exception as e:
            print(f"An error occurred while writing the file: {e}")

    def update_id_tag(self, id_tag: str, status: str, cardname: str, expiry_days: int = 365):
        """
        특정 ID Tag의 정보를 추가하거나 업데이트합니다.
        
        Args:
            id_tag: 업데이트할 ID 태그 문자열.
            status: 새로운 상태 (예: 'Accepted', 'Blocked', 'Invalid').
            cardname: 카드 소유자 이름.
            expiry_days: 만료까지 남은 일수 (기본값 365일).
        """
        data = self.load_data()
        
        # 만료일 계산 및 ISO 8601 형식으로 변환
        expiry_date = (datetime.now(timezone.utc) + timedelta(days=expiry_days))
        # 마이크로초 제거 및 OCPP 표준에 맞게 'Z'로 끝나는 ISO 형식으로 변환
        expiry_date_str = expiry_date.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        id_tags = data.get(ID_TAGS_KEY, {})
        
        # 데이터 업데이트/추가
        id_tags[id_tag] = {
            "status": status,
            "cardname": cardname,
            "expiryDate": expiry_date_str
        }
        data[ID_TAGS_KEY] = id_tags
        
        self.save_data(data)
        print(f"[ID Tag] '{id_tag}'이(가) 상태 '{status}'로 업데이트/추가되었습니다.")

    def delete_id_tag(self, id_tag: str):
        """특정 ID Tag를 데이터에서 삭제합니다."""
        data = self.load_data()
        id_tags = data.get(ID_TAGS_KEY, {})
        
        if id_tag in id_tags:
            del id_tags[id_tag]
            data[ID_TAGS_KEY] = id_tags
            self.save_data(data)
            print(f"[ID Tag] '{id_tag}'이(가) 삭제되었습니다.")
        else:
            print(f"[ID Tag] '{id_tag}'을(를) 찾을 수 없어 삭제를 건너뜁니다.")

    def get_nth_id_tag(self, n: int) -> Dict[str, Any]:
        """
        n번째 ID Tag의 정보를 반환합니다.
        
        Args:
            n: 0부터 시작하는 인덱스.
        
        Returns:
            해당 인덱스의 ID Tag 정보 딕셔너리. 존재하지 않으면 빈 딕셔너리 반환.
        """
        data = self.load_data()
        id_tags = data.get(ID_TAGS_KEY, {})
        
        if n < 0 or n >= len(id_tags):
            print(f"[ID Tag] 인덱스 {n}이(가) 범위를 벗어났습니다.")
            return {}
        
        id_tag_key = list(id_tags.keys())[n]
        # return {id_tag_key: id_tags[id_tag_key]}
        return id_tag_key


# --- 사용 예시 ---
if __name__ == '__main__':
    manager = JsonConfigManager(JSON_FILE)

    # 1. 새로운 ID Tag 추가/업데이트 예시
    print("\n--- 1. 새로운 ID Tag 추가 및 상태 업데이트 ---")
    manager.update_id_tag(
        id_tag="DEADBEEFCAFE0002", 
        status="Accepted", 
        cardname="Testing User2", 
        expiry_days=90 # 90일 후 만료
    )
    
    # 2. 기존 ID Tag 업데이트 예시 (상태 변경)
    print("\n--- 2. 기존 ID Tag 상태 변경 ---")
    manager.update_id_tag(
        id_tag="00000000790ACB20", 
        status="Invalid", 
        cardname="User B (Invalidated)", 
        expiry_days=365
    )

    # 3. ID Tag 삭제 예시
    print("\n--- 3. ID Tag 삭제 ---")
    manager.delete_id_tag("00000000F0C8FADD")
    
    # 4. 업데이트된 모든 데이터 출력하여 확인
    print("\n--- 4. 최종 데이터 확인 ---")
    final_data = manager.load_data()
    count = 0
    response = []
    for id_tag, info in final_data.get(ID_TAGS_KEY, {}).items():
        print(f"ID Tag: {id_tag}, Info: {info}")
        card = {'id': count, 'cardname': info.get('cardname', ''), 'cardnumber': id_tag, 'status': info.get('status', ''), 'expirydate': info.get('expiryDate', '')}
        response.append(card)
        count += 1
    print(json.dumps(response, indent=4, ensure_ascii=False))

    # 5. 특정 ID Tag 정보 읽기 예시
    print("\n--- 5. 특정 ID Tag 정보 읽기 ---")
    # final_data = manager.load_data()
    print(manager.get_nth_id_tag(1))  # 첫 번째 ID Tag 정보 출력