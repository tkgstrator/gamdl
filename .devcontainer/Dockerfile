FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build-dotnet

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

FROM mcr.microsoft.com/devcontainers/go:2.0.5-1.25-bookworm AS build-go

# amdecrypt
WORKDIR /
RUN git clone https://github.com/glomatico/amdecrypt.git --depth 1
WORKDIR /amdecrypt
RUN go mod tidy
RUN go build -o /usr/local/bin/amdecrypt main.go

FROM mcr.microsoft.com/devcontainers/python:3.0.2-3.10-bookworm AS build-python

RUN \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y \
    cmake

# mp4decrypt
WORKDIR /
RUN git clone https://github.com/axiomatic-systems/Bento4.git --depth 1
WORKDIR /Bento4
RUN mkdir cmakebuild
WORKDIR /Bento4/cmakebuild
RUN cmake -DCMAKE_BUILD_TYPE=Release ..
RUN make
RUN make install

# mp4box
WORKDIR /
RUN git clone https://github.com/gpac/gpac.git --depth 1
WORKDIR /gpac
RUN ls -la
RUN ./configure --static-mp4box
RUN make -j$(nproc)
RUN make install

FROM mcr.microsoft.com/devcontainers/python:3.10-bookworm

COPY --from=build-dotnet /usr/local/bin/N_m3u8DL-RE /usr/local/bin/
COPY --from=build-go /usr/local/bin/amdecrypt /usr/local/bin
COPY --from=build-python /usr/local/bin/mp4decrypt /usr/local/bin/
COPY --from=build-python /usr/local/bin/MP4Box /usr/local/bin/