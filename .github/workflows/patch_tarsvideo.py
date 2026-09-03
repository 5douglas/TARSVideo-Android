name: Build TARSVideo Android

on:
  workflow_dispatch:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 45

    steps:
      - name: Checkout TARSVideo
        uses: actions/checkout@v4

      - name: Checkout Jellyfin Android
        uses: actions/checkout@v4
        with:
          repository: jellyfin/jellyfin-android
          ref: master
          path: upstream

      - name: Setup Java 21
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"

      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@v4

      - name: Apply TARSVideo patch
        run: |
          set -e

          echo "=== Arquivos na raiz do repo ==="
          ls -la

          echo "=== Criando pasta do player ==="
          mkdir -p \
            upstream/app/src/main/java/org/jellyfin/mobile/player/vlc

          echo "=== Copiando player LibVLC ==="
          cp ./InternalVlcPlayerActivity.kt \
            upstream/app/src/main/java/org/jellyfin/mobile/player/vlc/InternalVlcPlayerActivity.kt

          echo "=== Aplicando patch TARSVideo ==="
          python3 ./patch_tarsvideo.py upstream

          echo "=== Patch concluído ==="

      - name: Build APK
        working-directory: upstream
        run: |
          chmod +x gradlew

          ./gradlew \
            assembleLibreDebug \
            --stacktrace

      - name: Collect APK
        run: |
          set -e

          mkdir -p dist

          echo "=== APKs encontrados ==="

          find upstream/app/build/outputs/apk \
            -type f \
            -name "*.apk" \
            -print

          APK="$(find upstream/app/build/outputs/apk \
            -type f \
            -name "*.apk" \
            | head -n 1)"

          if [ -z "$APK" ]; then
            echo "Nenhum APK encontrado."
            exit 1
          fi

          echo "APK encontrado:"
          echo "$APK"

          cp "$APK" \
            dist/TARSVideo-v0.1-debug.apk

          echo "=== APK final ==="
          ls -lh dist/TARSVideo-v0.1-debug.apk

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: TARSVideo-Android-v0.1
          path: dist/TARSVideo-v0.1-debug.apk
          retention-days: 14
          if-no-files-found: error
