import argparse
import hashlib
import importlib
import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import quote


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sanitize_script_name(script_name: str) -> str:
    if not script_name:
        return "shared"
    name = script_name.strip().replace(" ", "_")
    name = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", name)
    name = re.sub(r"_+", "_", name).strip("._-")
    return name or "shared"


def build_key(file_path: Path, key_prefix: str, script_name: str) -> str:
    digest = file_sha256(file_path)[:16]
    file_name = re.sub(r"[^\w\-\.\u4e00-\u9fff]", "_", file_path.name)
    parts = [p for p in [key_prefix.strip("/"), sanitize_script_name(script_name)] if p]
    prefix = "/".join(parts)
    return f"{prefix}/{digest}_{file_name}" if prefix else f"{digest}_{file_name}"


def build_public_url(bucket: str, region: str, scheme: str, key: str, public_base_url: str) -> str:
    encoded_key = quote(key, safe="/")
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/{encoded_key}"
    return f"{scheme}://{bucket}.cos.{region}.myqcloud.com/{encoded_key}"


def main() -> int:
    parser = argparse.ArgumentParser(description="上传本地图片到 COS，优先复用已存在对象并输出 URL")
    parser.add_argument("files", nargs="+", help="本地文件路径（可传多个）")
    parser.add_argument("--script-name", default="shared", help="剧本名，用于对象 key 分组")
    parser.add_argument("--region", default=os.getenv("COS_REGION", os.getenv("HUNYUAN_REGION", "ap-guangzhou")))
    parser.add_argument("--bucket", default=os.getenv("COS_BUCKET", ""))
    parser.add_argument("--key-prefix", default=os.getenv("COS_KEY_PREFIX", "refs"))
    parser.add_argument("--scheme", default=os.getenv("COS_SCHEME", "https"))
    parser.add_argument("--public-base-url", default=os.getenv("COS_PUBLIC_BASE_URL", ""))
    parser.add_argument("--signed", action="store_true", default=env_bool("COS_FORCE_SIGNED_URL", False))
    parser.add_argument("--expire-sec", type=int, default=int(os.getenv("COS_SIGNED_URL_EXPIRE_SEC", "3600")))
    parser.add_argument("--secret-id", default=os.getenv("COS_SECRET_ID", os.getenv("TENCENT_SECRET_ID", "")))
    parser.add_argument("--secret-key", default=os.getenv("COS_SECRET_KEY", os.getenv("TENCENT_SECRET_KEY", "")))
    parser.add_argument("--token", default=os.getenv("COS_TOKEN", os.getenv("TENCENT_TOKEN", "")))
    args = parser.parse_args()

    if not args.bucket:
        raise SystemExit("缺少 --bucket 或 COS_BUCKET")
    if not args.secret_id or not args.secret_key:
        raise SystemExit("缺少 COS/TENCENT 密钥（COS_SECRET_ID/COS_SECRET_KEY）")

    try:
        qcloud_cos = importlib.import_module("qcloud_cos")
        cos_exception = importlib.import_module("qcloud_cos.cos_exception")
        CosConfig = qcloud_cos.CosConfig
        CosS3Client = qcloud_cos.CosS3Client
        CosServiceError = cos_exception.CosServiceError
        CosClientError = cos_exception.CosClientError
    except Exception as exc:
        raise SystemExit("缺少依赖：cos-python-sdk-v5，请先安装") from exc

    config = CosConfig(
        Region=args.region,
        SecretId=args.secret_id,
        SecretKey=args.secret_key,
        Token=(args.token or None),
        Scheme=args.scheme,
    )
    client = CosS3Client(config)

    for raw in args.files:
        local_path = Path(raw).expanduser().resolve()
        if not local_path.is_file():
            print(f"[SKIP] 文件不存在: {local_path}")
            continue

        key = build_key(local_path, args.key_prefix, args.script_name)

        existed = False
        try:
            client.head_object(Bucket=args.bucket, Key=key)
            existed = True
        except (CosServiceError, CosClientError):
            existed = False

        if not existed:
            content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
            with local_path.open("rb") as fp:
                client.put_object(
                    Bucket=args.bucket,
                    Key=key,
                    Body=fp,
                    ContentType=content_type,
                )

        if args.signed:
            url = client.get_presigned_url(
                Method="GET",
                Bucket=args.bucket,
                Key=key,
                Expired=max(60, args.expire_sec),
            )
        else:
            url = build_public_url(args.bucket, args.region, args.scheme, key, args.public_base_url)

        state = "EXIST" if existed else "UPLOAD"
        print(f"[{state}] {local_path}")
        print(url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
