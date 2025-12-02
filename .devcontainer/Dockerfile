FROM mcr.microsoft.com/devcontainers/dotnet:9.0-bookworm AS build-dotnet

RUN \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y \
    clang-14

# N_m3u8DL-RE
WORKDIR /
RUN git clone https://github.com/nilaoda/N_m3u8DL-RE.git --depth 1
WORKDIR /N_m3u8DL-RE
RUN dotnet publish src/N_m3u8DL-RE \
    -r linux-arm64 \
    -c Release \
    -p:StripSymbols=true \
    -p:CppCompilerAndLinker=clang-14 \
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