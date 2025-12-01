FROM --platform=amd64 debian:13.2 AS build

SHELL ["/bin/bash", "-c"]

RUN \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    cmake \
    unzip \
    git \
    lsb-release \
    gnupg \
    aria2 \
    gcc-aarch64-linux-gnu

WORKDIR /app
RUN bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)"
RUN aria2c -o android-ndk-r23b-linux.zip https://dl.google.com/android/repository/android-ndk-r23b-linux.zip
RUN unzip -q -d ~ android-ndk-r23b-linux.zip
RUN rm android-ndk-r23b-linux.zip
RUN git clone https://github.com/WorldObservationLog/wrapper.git --depth 1 --recurse-submodules --branch arm64

WORKDIR /app/wrapper
RUN mkdir build
WORKDIR /app/wrapper/build
RUN cmake ..
RUN make

FROM debian:13.2

WORKDIR /app
COPY --from=build /app/wrapper/wrapper /usr/local/bin/wrapper
COPY --from=build /app/wrapper/wrapper /app/wrapper
COPY --from=build /app/wrapper/rootfs /app/rootfs
# COPY entrypoint.sh /app/entrypoint.sh
# N chmod +x /app/entrypoint.sh

CMD ["bash", "-c", "./wrapper ${args}"]

EXPOSE 10020 20020