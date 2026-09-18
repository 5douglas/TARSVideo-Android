# TARSVideo Android

O TARSVideo Android é uma personalização independente do cliente oficial
Jellyfin Android.

O projeto usa uma arquitetura baseada em patches em vez de manter uma cópia
completa permanente do código upstream.

## Como a build funciona

O GitHub Actions:

1. baixa um commit fixo do Jellyfin Android;
2. aplica os patches do TARSVideo;
3. adiciona recursos e configurações do projeto;
4. compila e assina o APK;
5. valida pacote, versão e certificado;
6. gera o artifact;
7. publica a release somente quando solicitado manualmente.

## Principais recursos

- branding TARSVideo
- JavaScript Injector
- player nativo Jellyfin/ExoPlayer
- DeviceId estável para SyncPlay
- notificações administrativas via FCM
- atualizador nativo
- verificação SHA-256
- validação de pacote e assinatura
- atualização automática opcional
- busca manual por atualizações
- seção Sobre o App

## Para criar sua própria versão

Substitua application ID, branding, servidor padrão, Firebase, assinatura,
URLs do updater e endpoints específicos do TARSVideo.

Não reutilize credenciais privadas do projeto.

TARSVideo não é um projeto oficial do Jellyfin.
