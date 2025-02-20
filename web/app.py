from flask import Flask, request, jsonify, render_template, redirect
from redis import Redis, RedisError
import random
import string
import webbrowser

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
char = string.digits + string.ascii_letters


def get_short_url():
    while True:
        code = "".join(random.choices(char, k=8))
        if not redis_client.exists(f"{code}"):
            return code


@app.route("/")
def starting_page():
    return render_template("shorturl.html")


@app.route("/shorten", methods=["POST"])
def shorten():
    try:
        data = request.get_json()
        long_url = data.get("url", None)

        if not long_url:
            return jsonify({"status": "error", "message": "請提供短網址"})

        check_url = redis_client.get(f"long:{long_url}")
        if check_url:
            return jsonify(
                {"status": "warning", "message": f"此連結已存在<br>{check_url}"}
            )

        short_url = get_short_url()

        redis_client.set(f"short:{short_url}", long_url)
        redis_client.set(f"long:{long_url}", short_url)

        return jsonify({"status": "success", "message": short_url})
    except RedisError as e:
        print(f"redis error: {e}")
        return jsonify({"status": "error", "message": "服務器繁忙，請稍後再試"})
    except Exception as e:
        print(f"shorten url error: {e}")
        return jsonify({"status": "error", "message": "伺服器繁忙，請稍後再次嘗試"})


@app.route("/<short_url>", methods=["GET"])
def redirect_link(short_url):
    try:
        long_url = redis_client.get(f"short:{short_url}")

        if not long_url:
            return jsonify({"status": "error", "message": "無此短網址"})

        count = redis_client.get(f"count:{short_url}")
        count = int(count) if count else 0
        count += 1
        redis_client.set(f"count:{short_url}", count)

        return redirect(long_url, code=302)

    except RedisError as e:
        print(f"redis error: {e}")
        return jsonify({"status": "error", "message": "服務器繁忙，請稍後再試"})
    except Exception as e:
        print(f"redirect link error: {e}")
        return jsonify({"status": "error", "message": "伺服器繁忙，請稍後再次嘗試"})


@app.route("/status/<short_url>", methods=["GET"])
def count(short_url):
    try:
        if not short_url:
            return jsonify({"錯誤": "無此短網址"})

        if not redis_client.get(f"short:{short_url}"):
            return jsonify({"錯誤": "短網址不存在"})

        count = redis_client.get(f"count:{short_url}")
        count = int(count) if count else 0

        return jsonify({"Link": short_url, "Visit": count})
    except RedisError as e:
        print(f"redis error: {e}")
        return jsonify({"status": "error", "message": "服務器繁忙，請稍後再試"})
    except Exception as e:
        print(f"count connect error: {e}")
        return jsonify({"status": "error", "message": "伺服器繁忙，請稍後再次嘗試"})


@app.route("/get_history", methods=["GET"])
def get_history():
    try:
        cursor = 0
        total_url = {}

        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match="short:*", count=30)
            for key in keys:
                count_key = key.replace("short:","")
                long_url=redis_client.get(key)
                if long_url:
                    total_url[key] = {}
                    total_url[key]["long"] = long_url

                    count = redis_client.get(f"count:{count_key}")
                    total_url[key]["count"] = int(count) if count else 0
            if cursor == 0:
                break

        return jsonify(total_url)
    except RedisError as e:
        print(f"redis error: {e}")
    except Exception as e:
        print(f"count connect error: {e}")


if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5050")
    app.run(debug=False, host="0.0.0.0", port=5050, use_reloader=False)
