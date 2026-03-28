ARG GAMDL_VERSION=2.8
ARG N_M3U8DL_RE_VERSION=v0.5.1-beta
ARG AMDECRYPT_VERSION=0.0.1
ARG BENTO4_VERSION=v1.6.0-641
ARG GPAC_VERSION=v2.4.0
ARG PYTHON_VERSION=3.10
ARG BASE_IMAGE=bookworm

FROM dhi.io/dotnet:10-sdk AS build-dotnet

ARG N_M3U8DL_RE_VERSION
ARG TARGETARCH

RUN \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git clang

WORKDIR /
RUN git clone https://github.com/nilaoda/N_m3u8DL-RE.git --depth 1
WORKDIR /N_m3u8DL-RE
# Fix C# 14 breaking change: 'this' not allowed in nameof() in attributes
RUN sed -i 's/nameof(this\.\([a-zA-Z]*\))/nameof(\1)/g' \
    src/N_m3u8DL-RE.Parser/StreamExtractor.cs
RUN \
    --mount=type=cache,target=/root/.nuget/packages \
    case "${TARGETARCH}" in \
    arm64) RID="linux-arm64" ;; \
    amd64) RID="linux-x64"  ;; \
    *)     echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac && \
    dotnet publish src/N_m3u8DL-RE \
    -r "${RID}" \
    -c Release \
    -p:StripSymbols=true \
    -p:CppCompilerAndLinker=clang \
    -o /usr/local/bin

FROM golang:1.25.8-bookworm AS build-go

ARG AMDECRYPT_VERSION

# amdecrypt
WORKDIR /
RUN git clone https://github.com/glomatico/amdecrypt.git && \
    cd amdecrypt && git checkout ${AMDECRYPT_VERSION}
WORKDIR /amdecrypt
RUN go mod tidy
RUN go build -o /usr/local/bin/amdecrypt main.go

FROM python:3.12 AS build-python

ARG BENTO4_VERSION
ARG GPAC_VERSION

RUN \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y \
    cmake

# mp4decrypt
WORKDIR /
RUN git clone https://github.com/axiomatic-systems/Bento4.git && \
    cd Bento4 && git checkout ${BENTO4_VERSION}
WORKDIR /Bento4
RUN mkdir cmakebuild
WORKDIR /Bento4/cmakebuild
RUN cmake -DCMAKE_BUILD_TYPE=Release ..
RUN make
RUN make install

# mp4box
WORKDIR /
RUN git clone https://github.com/gpac/gpac.git && \
    cd gpac && git checkout ${GPAC_VERSION}
WORKDIR /gpac
RUN ./configure --static-mp4box
RUN make -j$(nproc)
RUN make install

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-${BASE_IMAGE}

ARG GAMDL_VERSION

RUN \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update && apt-get install -y \
  ffmpeg

COPY --from=build-dotnet /usr/local/bin/N_m3u8DL-RE /usr/local/bin/
COPY --from=build-go /usr/local/bin/amdecrypt /usr/local/bin
COPY --from=build-python /usr/local/bin/mp4decrypt /usr/local/bin/
COPY --from=build-python /usr/local/bin/MP4Box /usr/local/bin/

WORKDIR /app
RUN uv pip install --system "gamdl==${GAMDL_VERSION}"

CMD ["/bin/bash"]