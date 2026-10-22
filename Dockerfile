ARG N_M3U8DL_RE_COMMIT=81241369995ca93cef9d64a7a309963373fc796d
ARG PYTHON_VERSION=3.10
ARG BASE_IMAGE=bookworm

# Official multi-arch .NET 10 SDK; only its portable /usr/share/dotnet is used.
FROM mcr.microsoft.com/dotnet/sdk:10.0@sha256:747cbade5bfd918a175ac32f8f1d931edec2c7d0d5397a3de72eaef1ac1f66d2 AS dotnet-sdk

# Build NativeAOT against the oldest shipped runtime libc (bookworm, glibc 2.36)
# so the helper starts on every runtime variant. Target-native, no cross build.
FROM debian:bookworm-slim@sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8 AS build-dotnet

ARG N_M3U8DL_RE_COMMIT
ARG TARGETARCH

ENV DOTNET_ROOT=/usr/share/dotnet \
    PATH=/usr/share/dotnet:${PATH} \
    DOTNET_NOLOGO=1 \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1

RUN \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git clang binutils file zlib1g-dev libssl-dev libicu72

COPY --from=dotnet-sdk /usr/share/dotnet /usr/share/dotnet
RUN dotnet --info

WORKDIR /N_m3u8DL-RE
RUN git init -q . && \
    git remote add origin https://github.com/nilaoda/N_m3u8DL-RE.git && \
    git fetch --depth 1 origin "${N_M3U8DL_RE_COMMIT}" && \
    git checkout -q FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${N_M3U8DL_RE_COMMIT}"
RUN \
    --mount=type=cache,target=/root/.nuget/packages \
    set -eu; \
    case "${TARGETARCH}" in \
    arm64) RID="linux-arm64"; command -v aarch64-linux-gnu-objcopy ;; \
    amd64) RID="linux-x64" ;; \
    *)     echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    dotnet publish src/N_m3u8DL-RE \
    -r "${RID}" \
    -c Release \
    -p:StripSymbols=true \
    -p:CppCompilerAndLinker=clang \
    -o /out
# Fail the build if the helper is not a native ELF or needs glibc newer than 2.36.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -eu; \
    bin=/out/N_m3u8DL-RE; \
    test -s "${bin}"; \
    file "${bin}" > /tmp/file.txt; \
    cat /tmp/file.txt; \
    grep -q 'ELF' /tmp/file.txt; \
    objdump -T "${bin}" > /tmp/dynsyms.txt; \
    grep -o 'GLIBC_[0-9][0-9.]*' /tmp/dynsyms.txt | sed 's/^GLIBC_//' | sort -uV > /tmp/glibc.txt; \
    test -s /tmp/glibc.txt; \
    max="$(tail -n 1 /tmp/glibc.txt)"; \
    test -n "${max}"; \
    echo "Max required GLIBC: ${max}"; \
    test "$(printf '%s\n%s\n' "${max}" 2.36 | sort -V | tail -n 1)" = "2.36"; \
    ! grep -q 'GLIBC_2\.38' /tmp/dynsyms.txt

FROM rust:1-bookworm AS build-python

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ARG PYTHON_VERSION
WORKDIR /src
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY gamdl/ ./gamdl/
RUN uv build --python "${PYTHON_VERSION}" --wheel --out-dir /wheels && \
    uv export --frozen --no-dev --no-emit-project --output-file /wheels/requirements.txt

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-${BASE_IMAGE}

# ffmpeg is still required when using the N_m3u8DL-RE download mode.
# gamdl 3.6+ does native muxing/decryption, so mp4decrypt/MP4Box/amdecrypt are no longer needed.
RUN \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg

COPY --from=build-dotnet /out/N_m3u8DL-RE /usr/local/bin/

WORKDIR /app
RUN --mount=type=bind,from=build-python,source=/wheels,target=/wheels \
    uv pip install --system -r /wheels/requirements.txt /wheels/*.whl

# Build-time ABI gate: both the Python CLI and the NativeAOT helper must start.
RUN python -m gamdl --help > /dev/null && N_m3u8DL-RE --help > /dev/null

CMD ["/bin/bash"]
