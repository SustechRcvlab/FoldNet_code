#!/usr/bin/env bash
set -euo pipefail

# FoldNet one-shot installer (micromamba-first)
# Usage:
#   bash install_foldnet.sh
#   bash install_foldnet.sh --run-blender-test --run-init-assets --run-pyflex-test
#   bash install_foldnet.sh --blender-path /path/to/blender-4.2.9-linux-x64

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="FoldNet"
PYTHON_VERSION="3.9.20"
BLENDER_VERSION="4.2.9"
BLENDER_ARCH="linux-x64"
BLENDER_DIR_DEFAULT="${REPO_ROOT}/blender-${BLENDER_VERSION}-${BLENDER_ARCH}"
BLENDER_URL="https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-${BLENDER_ARCH}.tar.xz"

RUN_BLENDER_TEST=0
RUN_INIT_ASSETS=0
RUN_PYFLEX_TEST=0
SKIP_APT=0
BLENDER_PATH="${BLENDER_DIR_DEFAULT}"

log() { printf "\033[1;32m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; exit 1; }

usage() {
    cat <<EOF
FoldNet installer

Options:
  --env-name NAME          micromamba/conda env name (default: ${ENV_NAME})
  --python VERSION         python version (default: ${PYTHON_VERSION})
  --blender-path PATH      existing blender root path
  --run-blender-test       run blender --run_test after install
  --run-init-assets        run blender --run_init to download assets
  --run-pyflex-test        run pyflex import/init test
  --skip-apt               skip apt dependency install
  -h, --help               show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env-name) ENV_NAME="$2"; shift 2 ;;
        --python) PYTHON_VERSION="$2"; shift 2 ;;
        --blender-path) BLENDER_PATH="$2"; shift 2 ;;
        --run-blender-test) RUN_BLENDER_TEST=1; shift ;;
        --run-init-assets) RUN_INIT_ASSETS=1; shift ;;
        --run-pyflex-test) RUN_PYFLEX_TEST=1; shift ;;
        --skip-apt) SKIP_APT=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) err "Unknown option: $1" ;;
    esac
done

append_if_missing() {
    local file="$1"
    local block="$2"
    local key="$3"
    touch "${file}"
    if ! grep -q "${key}" "${file}"; then
        printf "\n%s\n" "${block}" >> "${file}"
    fi
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || err "Missing command: $1"
}

run_in_env() {
    if command -v micromamba >/dev/null 2>&1; then
        micromamba run -n "${ENV_NAME}" "$@"
    elif command -v conda >/dev/null 2>&1; then
        conda run -n "${ENV_NAME}" "$@"
    else
        err "Neither micromamba nor conda is available."
    fi
}

create_env() {
    if command -v micromamba >/dev/null 2>&1; then
        if micromamba env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
            log "micromamba env ${ENV_NAME} already exists, skip creation."
        else
            log "Creating micromamba env ${ENV_NAME} (python=${PYTHON_VERSION})..."
            micromamba create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}" pip
        fi
        return
    fi

    if command -v conda >/dev/null 2>&1; then
        if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
            log "conda env ${ENV_NAME} already exists, skip creation."
        else
            log "Creating conda env ${ENV_NAME} (python=${PYTHON_VERSION})..."
            conda create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}" pip
        fi
        return
    fi

    err "Please install micromamba first (recommended), or conda."
}

install_apt_deps() {
    if [[ "${SKIP_APT}" -eq 1 ]]; then
        warn "Skip apt dependencies by --skip-apt"
        return
    fi

    if ! command -v apt >/dev/null 2>&1; then
        warn "apt not found, skip system dependency install."
        return
    fi

    if ! command -v sudo >/dev/null 2>&1; then
        warn "sudo not found, skip apt install."
        return
    fi

    log "Installing apt packages..."
    sudo apt update
    # libasound2 is now virtual on new Ubuntu; libasound2t64 is the real package name.
    local alsa_pkg="libasound2"
    if apt-cache show libasound2t64 >/dev/null 2>&1; then
        alsa_pkg="libasound2t64"
    fi
    sudo apt install -y --no-install-recommends ffmpeg libsm6 "${alsa_pkg}" libegl1 fonts-freefont-ttf xz-utils wget
}

setup_repo() {
    cd "${REPO_ROOT}"
    require_cmd git

    if [[ ! -d ".git" ]]; then
        err "Not a git repository: ${REPO_ROOT}"
    fi

    # Ensure submodules use HTTPS (avoid ssh key requirement)
    declare -A SUBMODULES=(
        ["external/python-urx"]="https://github.com/chen01yx/python-urx.git"
        ["external/batch_urdf"]="https://github.com/chen01yx/batch_urdf.git"
        ["external/bpycv"]="https://github.com/chen01yx/bpycv.git"
        ["external/Paint-it"]="https://github.com/Bowie375/Paint-it.git"
    )
    for path in "${!SUBMODULES[@]}"; do
        git config -f .gitmodules "submodule.${path}.url" "${SUBMODULES[$path]}"
    done
    git submodule sync --recursive

    log "Updating submodules..."
    git submodule update --init --recursive
}

install_python_deps() {
    cd "${REPO_ROOT}"
    log "Installing FoldNet python package..."
    run_in_env pip install -e . --use-pep517
    run_in_env bash setup.sh
}

install_blender() {
    cd "${REPO_ROOT}"
    mkdir -p "${REPO_ROOT}"

    if [[ -x "${BLENDER_PATH}/blender" ]]; then
        log "Using existing blender at ${BLENDER_PATH}"
    else
        require_cmd wget
        require_cmd tar
        log "Downloading Blender ${BLENDER_VERSION}..."
        wget -c "${BLENDER_URL}" -O /tmp/foldnet_blender.tar.xz
        tar -xJf /tmp/foldnet_blender.tar.xz -C "${REPO_ROOT}"
        rm -f /tmp/foldnet_blender.tar.xz
        BLENDER_PATH="${BLENDER_DIR_DEFAULT}"
    fi

    local blender_bin="${BLENDER_PATH}/blender"
    local blender_python="${BLENDER_PATH}/4.2/python/bin/python3.11"
    [[ -x "${blender_bin}" ]] || err "blender binary not found: ${blender_bin}"
    [[ -x "${blender_python}" ]] || err "blender python not found: ${blender_python}"

    log "Installing Blender python packages..."
    "${blender_python}" -m pip install -e "${REPO_ROOT}/external/batch_urdf"
    "${blender_python}" -m pip install -e "${REPO_ROOT}/external/bpycv"
    "${blender_python}" -m pip install psutil

    local blender_block="# >>> foldnet blender >>>
export BLENDER_PATH=\"${BLENDER_PATH}\"
export PATH=\"\$BLENDER_PATH:\$PATH\"
alias blender_python=\"${blender_python}\"
# <<< foldnet blender <<<"

    append_if_missing "${HOME}/.bashrc" "${blender_block}" "foldnet blender"
    append_if_missing "${HOME}/.zshrc" "${blender_block}" "foldnet blender"

    if [[ "${RUN_BLENDER_TEST}" -eq 1 ]]; then
        log "Running blender --run_test ..."
        "${blender_bin}" "${REPO_ROOT}/src/garmentds/foldenv/scene.blend" \
          --python "${REPO_ROOT}/src/garmentds/foldenv/blender_script.py" \
          --background -- --run_test
    fi

    if [[ "${RUN_INIT_ASSETS}" -eq 1 ]]; then
        log "Running blender --run_init ..."
        "${blender_bin}" "${REPO_ROOT}/src/garmentds/foldenv/scene.blend" \
          --python "${REPO_ROOT}/src/garmentds/foldenv/blender_script.py" \
          --background -- --run_init
    fi
}

setup_pyflex_env() {
    local pyflex_path="${REPO_ROOT}/src/pyflex"
    [[ -d "${pyflex_path}/libs" ]] || err "Missing pyflex libs: ${pyflex_path}/libs"

    export PYFLEX_PATH="${pyflex_path}"
    export PYTHONPATH="${pyflex_path}/libs:${PYTHONPATH:-}"
    # Put WSL CUDA stubs first if present so libcuda is discoverable.
    if [[ -d /usr/lib/wsl/lib ]]; then
        export LD_LIBRARY_PATH="/usr/lib/wsl/lib:${pyflex_path}/libs:${LD_LIBRARY_PATH:-}"
    else
        export LD_LIBRARY_PATH="${pyflex_path}/libs:${LD_LIBRARY_PATH:-}"
    fi

    local pyflex_block="# >>> foldnet pyflex >>>
export PYFLEX_PATH=\"${pyflex_path}\"
export PYTHONPATH=\"\$PYFLEX_PATH/libs:\$PYTHONPATH\"
if [ -d /usr/lib/wsl/lib ]; then
  export LD_LIBRARY_PATH=\"/usr/lib/wsl/lib:\$PYFLEX_PATH/libs:\$LD_LIBRARY_PATH\"
else
  export LD_LIBRARY_PATH=\"\$PYFLEX_PATH/libs:\$LD_LIBRARY_PATH\"
fi
# <<< foldnet pyflex <<<"

    append_if_missing "${HOME}/.bashrc" "${pyflex_block}" "foldnet pyflex"
    append_if_missing "${HOME}/.zshrc" "${pyflex_block}" "foldnet pyflex"

    if [[ "${RUN_PYFLEX_TEST}" -eq 1 ]]; then
        log "Running pyflex test..."
        run_in_env python -c "import pyflex; pyflex.init(True, False, 0, 0, 0); print('pyflex ok')"
    fi
}

main() {
    log "Repo root: ${REPO_ROOT}"
    setup_repo
    install_apt_deps
    create_env
    install_python_deps
    install_blender
    setup_pyflex_env

    cat <<EOF

Install finished.

Next:
  1) Activate env: micromamba activate ${ENV_NAME}
  2) Reload shell: source ~/.bashrc   (or ~/.zshrc)
  3) Optional full test:
     CUDA_VISIBLE_DEVICES=0 python run/fold_multi_cat.py env.cloth_obj_path=asset/garment_example/0/mesh.obj env.render_process_num=1 '+env.init_cloth_vel_range=[1.,2.]'

If you want blender tests during install, rerun with:
  --run-blender-test --run-init-assets
EOF
}

main "$@"
# 注意：我无法在这里直接创建 libcuda.so 的 sudo 符号链接（sandbox 禁用了 sudo 提权）。如果仍报找不到 libcuda.so，可手动执行：

# sudo ln -sf /usr/lib/wsl/lib/libcuda.so.1 /usr/lib/x86_64-linux-gnu/libcuda.so.1
# sudo ln -sf /usr/lib/wsl/lib/libcuda.so   /usr/lib/x86_64-linux-gnu/libcuda.so
# sudo ldconfig
# 再跑上面的测试命令。