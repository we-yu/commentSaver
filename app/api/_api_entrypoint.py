from fastapi import FastAPI
# 他の必要なインポート

app = FastAPI()

@app.get("/test-list-processor")
def test_list_processor():
    # list_processorのテスト用関数を呼び出す
    return {"message": "Test function called successfully"}
