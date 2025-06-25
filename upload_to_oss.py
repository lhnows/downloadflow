import os
import requests
import oss2
from urllib.parse import urlparse

# --- 1. 从环境变量获取阿里云 OSS 配置 ---
# 这些变量将在 GitHub Actions 的 secrets 中设置
access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
bucket_name = os.getenv('OSS_BUCKET_NAME')
endpoint = os.getenv('OSS_ENDPOINT') # 例如：oss-cn-hangzhou.aliyuncs.com

# 检查环境变量是否都已设置
if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
    print("错误：必要的 OSS 环境变量未设置完整。请检查 GitHub Secrets。")
    exit(1)

# --- 2. 初始化 OSS Bucket ---
auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, endpoint, bucket_name)

# --- 3. 定义文件路径 ---
links_file_path = 'links.txt'

def process_links():
    """
    读取、下载、上传并更新链接
    """
    try:
        with open(links_file_path, 'r') as f:
            original_urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: {links_file_path} 文件未找到。")
        return

    if not original_urls:
        print("links.txt 文件为空，无需操作。")
        return

    new_oss_urls = []

    print("开始处理下载链接...")
    for url in original_urls:
        # 如果链接已经是 OSS 链接，则跳过
        if f'.{endpoint}' in url:
            print(f"跳过已是 OSS 链接: {url}")
            new_oss_urls.append(url)
            continue
            
        try:
            print(f"正在下载: {url}")
            # 从 URL 中提取文件名
            parsed_url = urlparse(url)
            object_name = os.path.basename(parsed_url.path)
            
            if not object_name:
                object_name = "default_filename" # 如果 URL 路径为空，提供一个默认名称

            # 使用流式下载处理大文件
            with requests.get(url, stream=True) as r:
                r.raise_for_status()  # 如果请求失败 (如 404), 会抛出异常
                
                print(f"正在上传 {object_name} 到 OSS...")
                # 直接将响应内容流上传到 OSS，避免写入本地磁盘
                bucket.put_object(object_name, r.content)

            # 生成 OSS 的公开访问 URL
            # 格式: https://<bucket-name>.<endpoint>/<object-name>
            oss_url = f"https://{bucket_name}.{endpoint}/{object_name}"
            print(f"上传成功! OSS URL: {oss_url}")
            new_oss_urls.append(oss_url)

        except requests.exceptions.RequestException as e:
            print(f"下载文件失败: {url}, 错误: {e}")
            new_oss_urls.append(f"FAILED_DOWNLOAD: {url}")
        except oss2.exceptions.OssError as e:
            print(f"上传到 OSS 失败: {url}, 错误: {e}")
            new_oss_urls.append(f"FAILED_UPLOAD: {url}")
        except Exception as e:
            print(f"处理链接时发生未知错误: {url}, 错误: {e}")
            new_oss_urls.append(f"FAILED_UNKNOWN: {url}")


    # --- 5. 将新的 OSS URL 写回文件 ---
    print("\n所有链接处理完毕，正在更新 links.txt...")
    with open(links_file_path, 'w') as f:
        for url in new_oss_urls:
            f.write(url + '\n')
    
    print("links.txt 文件更新成功。")

if __name__ == "__main__":
    process_links()
