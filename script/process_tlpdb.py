#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import tarfile
import io


def process_package(package_name, runfiles, repo_path, debug=False):
    """
    处理单个包：从原始包中提取文件，并返回最终要打包的文件列表。

    Returns:
        list: 一个包含 (新归档中的文件名, 源归档中的文件路径) 元组的列表。
              如果处理失败，返回 None。
    """
    source_tar_path = os.path.join(repo_path, f"{package_name}.tar.xz")

    if not os.path.exists(source_tar_path):
        if debug:
            print(f"[DEBUG] 警告: 包文件 '{source_tar_path}' 不存在，跳过此包。")
        return None

    final_files = []
    try:
        with tarfile.open(source_tar_path, "r:xz") as tar_in:
            # 准备最终要打包的文件列表
            for file_path in runfiles:
                # 检查是否是amsfonts包且路径包含/cm/cm
                is_amsfonts_with_cm = (
                    (package_name == "amsfonts" or package_name == "cm") and "/cm/cm" in file_path
                )

                if not is_amsfonts_with_cm and (
                    file_path.startswith("fonts/")
                    or file_path.startswith("texmf-dist/fonts/")
                    or file_path.endswith(".pdf")
                    or file_path.endswith(".pdb")
                    or file_path.endswith(".h")
                    or file_path.endswith(".c")
                    or file_path.endswith(".txt")
                    or file_path.endswith(".xml")
                    or file_path.endswith(".pl")
                    or file_path.endswith(".pm")
                    or file_path.endswith(".lua")
                    or file_path.endswith(".htf")
                    or file_path.endswith(".xdy")
                    or file_path.endswith(".dll")
                    or file_path.endswith(".so")
                    or file_path.endswith(".jar")
                    or file_path.endswith(".sh")
                    or file_path.endswith(".dat")
                    or file_path.endswith(".jpg")
                    or file_path.endswith(".jpeg")
                    or file_path.endswith(".png")
                    or file_path.endswith(".ttf")
                    or file_path.endswith(".otf")
                    or file_path.endswith(".afm")
                    or file_path.endswith(".map")
                    or file_path.endswith(".enc")
                    or file_path.endswith(".vpl")
                    or file_path.endswith(".lua")
                    or file_path.endswith("DroidSansFallback.ttf")
                ):
                    if debug:
                        print(f"[DEBUG] 跳过文件 '{file_path}' (文件名)")
                    continue

                # 获取文件名（用于新包）
                filename = os.path.basename(file_path)
                if not filename:
                    continue

                # 查找文件在原始包中的完整路径
                # tlpdb 中的 RELOC/ 前缀对应原始包中的直接路径
                source_member_path = file_path

                try:
                    member = tar_in.getmember(source_member_path)
                    final_files.append((filename, source_member_path))
                    if debug:
                        print(
                            f"[DEBUG] 准备打包: '{filename}' (来自 '{source_member_path}')"
                        )
                except KeyError:
                    if debug:
                        print(
                            f"[DEBUG] 警告: 在 '{source_tar_path}' 中找不到文件 '{source_member_path}'"
                        )
                    continue
    except (tarfile.TarError, EOFError) as e:
        if debug:
            print(f"[DEBUG] 错误: 无法读取包文件 '{source_tar_path}': {e}")
        return None

    return final_files


def create_repacked_archive(package_name, files_to_pack, debug=False, repo_path=""):
    """
    创建重新打包的 .tar.xz 文件。

    Args:
        package_name (str): 包名。
        files_to_pack (list): 包含 (新归档中的文件名, 源归档中的文件路径) 元组的列表。
    """
    if not files_to_pack:
        return

    run_dir = "./run"
    os.makedirs(run_dir, exist_ok=True)
    output_tar_path = os.path.join(run_dir, f"{package_name}.tar.xz")
    source_tar_path = os.path.join(repo_path, f"{package_name}.tar.xz")

    try:
        with tarfile.open(output_tar_path, "w:xz") as tar_out, tarfile.open(
            source_tar_path, "r:xz"
        ) as tar_in:

            for filename, source_path in files_to_pack:
                try:
                    member = tar_in.getmember(source_path)
                    fileobj = tar_in.extractfile(member)

                    # 创建新的 TarInfo 对象，只包含文件名
                    new_tarinfo = tarfile.TarInfo(name=filename)
                    new_tarinfo.size = member.size
                    new_tarinfo.mtime = member.mtime

                    # 将文件内容写入新归档
                    tar_out.addfile(new_tarinfo, fileobj=fileobj)
                except KeyError:
                    if debug:
                        print(f"[DEBUG] 警告: 创建归档时找不到源文件 '{source_path}'")

        if debug:
            print(f"[DEBUG] 成功创建重新打包的文件: '{output_tar_path}'")

    except (tarfile.TarError, FileNotFoundError) as e:
        print(f"错误: 无法创建重新打包的文件 '{output_tar_path}': {e}")


def parse_and_repack(tlpdb_path, output_path, repo_path, debug=False):
    """
    主解析函数：读取 tlpdb，处理包，生成输出文件和重新打包的归档。
    """
    try:
        with open(tlpdb_path, "r", encoding="utf-8") as f_in, open(
            output_path, "w", encoding="utf-8"
        ) as f_out:

            content = f_in.read()
            package_entries = content.strip().split("\n\n")

            for entry in package_entries:
                lines = entry.strip().split("\n")
                package_name = None
                runfiles = []
                in_runfiles_section = False

                # --- 新的过滤规则 ---
                skip_package = False

                for line in lines:
                    if not line.strip():
                        continue

                    if line.startswith("name "):
                        package_name = line.split(" ", 1)[1].strip()
                        if debug:
                            print(f"\n[DEBUG] 正在解析包: {package_name}")

                        # 规则1: 跳过以 '-dev' 结尾的包
                        if package_name.endswith("-dev"):
                            if debug:
                                print(
                                    f"[DEBUG] 包 '{package_name}' 以 '-dev' 结尾，已跳过。"
                                )
                            skip_package = True

                        # 规则2: 跳过以 '00' 开头的包
                        if package_name.startswith("00"):
                            if debug:
                                print(
                                    f"[DEBUG] 包 '{package_name}' 以 '00' 开头，已跳过。"
                                )
                            skip_package = True

                    elif line.startswith("runfiles") and not skip_package:
                        in_runfiles_section = True

                    elif in_runfiles_section and (
                        line.startswith(" ") or line.startswith("\t")
                    ):
                        file_path = line.strip()
                        if file_path.startswith("RELOC/"):
                            file_path = file_path[6:]
                        runfiles.append(file_path)

                    elif (
                        line and not line.startswith(" ") and not line.startswith("\t")
                    ):
                        in_runfiles_section = False

                # --- 处理符合条件的包 ---
                if package_name and not skip_package and runfiles:
                    files_to_pack = process_package(
                        package_name, runfiles, repo_path, debug
                    )

                    if files_to_pack:
                        # 1. 创建重新打包的归档
                        create_repacked_archive(
                            package_name, files_to_pack, debug, repo_path
                        )

                        # 2. 生成与打包内容一致的输出文件
                        if debug:
                            print(
                                f"[DEBUG] 包 '{package_name}' 处理完成，正在写入输出文件..."
                            )

                        f_out.write(f"{package_name} {len(files_to_pack)}\n")
                        for filename, _ in files_to_pack:
                            f_out.write(f"{filename}\n")
                        f_out.write("\n")

                elif package_name and not skip_package and debug:
                    print(
                        f"[DEBUG] 包 '{package_name}' 没有 runfiles 或处理失败，已跳过。"
                    )

    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{tlpdb_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"处理文件时发生错误: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="解析 tlpdb，提取 runfiles 并从源仓库重新打包。",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input_file", help="输入的 texlive.tlpdb 文件路径。")
    parser.add_argument("output_file", help="输出结果的文件路径。")
    parser.add_argument("repo", help="存储原始 .tar.xz 包的仓库目录路径。")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="启用调试模式，输出详细处理信息。"
    )

    args = parser.parse_args()

    if args.debug:
        print("--- 调试模式已开启 ---")
        print(f"输入文件: {args.input_file}")
        print(f"输出文件: {args.output_file}")
        print(f"仓库目录: {args.repo}")
        print("-" * 20)

    parse_and_repack(args.input_file, args.output_file, args.repo, args.debug)

    if args.debug:
        print("-" * 20)
        print("--- 处理完成 ---")


def find_and_save_vf_files():
    """
    在Linux系统中查找/usr/local/texlive目录下所有.vf结尾的文件，
    提取文件名排序后写入/tmp/vf.txt，无控制台输出
    """
    vf_filenames = []
    target_dir = "/usr/local/texlive"
    try:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".vf") or file.endswith(".fontspec"):
                    filename = os.path.basename(file)
                    vf_filenames.append(filename)

    except PermissionError:
        pass
    except Exception:
        pass

    vf_filenames.sort()
    try:
        with open("/tmp/vf.txt", "w", encoding="utf-8") as f:
            for name in vf_filenames:
                f.write(f"{name}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
    find_and_save_vf_files()
