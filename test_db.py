import os
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

# 1. .envファイルの読み込み
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ エラー: .env ファイルに DATABASE_URL が設定されていません。")
    exit(1)

# パスワード部分を隠して接続先を表示（セキュリティ配慮）
masked_url = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else "不明なURL"
print(f"🔌 接続先データベース: {masked_url}\n")

try:
    # 2. データベースエンジンの作成
    engine = create_engine(DATABASE_URL)
    
    # 3. データベースのメタデータを取得（全テーブルの構造を自動読み込み）
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    table_names = metadata.tables.keys()
    
    if not table_names:
        print("⚠️ データベース接続には成功しましたが、テーブルが一つも見つかりません。")
    else:
        print(f"📂 検出されたテーブル一覧: {', '.join(table_names)}\n")
        
        # 4. 各テーブルの情報を順番に取得して表示
        with engine.connect() as connection:
            for table_name in table_names:
                print(f"{"="*40}")
                print(f"📊 テーブル: {table_name}")
                print(f"{"="*40}")
                
                table = metadata.tables[table_name]
                
                # カラム情報（group_idなどの存在確認）
                columns = [col.name for col in table.columns]
                print(f"📝 カラム構成: {', '.join(columns)}")
                
                # データの取得テスト（最大3件だけ取得）
                query = table.select().limit(3)
                result = connection.execute(query)
                rows = result.fetchall()
                
                if rows:
                    print("✅ データサンプル (最大3件):")
                    for row in rows:
                        # SQLAlchemy 2.0 に対応した辞書形式での出力
                        print(dict(row._mapping))
                else:
                    print("⚠️ レコード（データ）が登録されていません。")
                print("\n")
                
    print("🎉 すべてのデータベーステストが正常に完了しました！")

except Exception as e:
    print(f"❌ データベース接続エラーが発生しました:\n{e}")