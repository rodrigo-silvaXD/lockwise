// ---------------------------------------------------------------------------
// LOCKWISE — ponte de hardware entre o circuito lógico e a API na nuvem
//
// O QUE ESTE PROGRAMA NÃO FAZ
//
// Ele não decide nada. O comparador de senha, a máquina de estados e o contador
// de tentativas continuam sendo portas lógicas e flip-flops, montados no
// simulador ao lado. Se a lógica viesse para cá, o projeto perderia justamente
// o que o requisito de eletrônica digital pede.
//
// O QUE ELE FAZ
//
// Lê os pinos de saída do circuito, percebe quando o estado muda e envia o
// evento correspondente para a API por HTTPS. É o gateway em Python
// (gateway/lockwise_gateway) reescrito para rodar no hardware — e é o que
// elimina o passo manual descrito como limitação no relatório do projeto.
//
// LIGAÇÕES ESPERADAS
//
//   GPIO 16  ←  AGUARDANDO     (saída do circuito)
//   GPIO 17  ←  VERIFICANDO
//   GPIO 18  ←  TRAVA_ABERTA
//   GPIO 19  ←  BLOQUEADO
//   GPIO 21  ←  ERROS_C1       (bit alto do contador)
//   GPIO 22  ←  ERROS_C0       (bit baixo do contador)
//
// Se o circuito lógico ainda não estiver montado, deixe MODO_ENSAIO ligado:
// o programa gera as transições sozinho, o que serve para provar a rede antes
// de existir hardware para ler.
// ---------------------------------------------------------------------------

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <time.h>

// --------------------------------------------------------------- configuração

// Rede virtual do Wokwi. Sem senha, e só existe dentro do simulador.
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_SENHA = "";

const char* API = "https://lockwise-api.onrender.com";

// ATENÇÃO: um projeto público no Wokwi expõe esta chave para qualquer um.
// Use uma chave dedicada a este simulador, nunca a mesma do gateway. A API
// aceita várias chaves separadas por vírgula em LOCKWISE_API_KEY, justamente
// para que esta possa ser revogada sozinha (ver docs/adr/0029).
const char* API_KEY = "COLE_AQUI_A_CHAVE_DO_SIMULADOR";

// Energia de uma liberação, em milijoules (docs/fisica.md §6):
// (12 V × 292,5 mA + 5 V × 4,3 mA) × 5,16 s ≈ 18,2 J.
const int ENERGIA_LIBERACAO_MJ = 18200;

// O circuito tem uma senha gravada, logo um morador. Registro 1 da tabela.
const int USUARIO_MORADOR = 1;

// Sem hardware ligado, gera transições para provar o caminho até a API.
#define MODO_ENSAIO 1

// Pinos de leitura
const int PINO_AGUARDANDO   = 16;
const int PINO_VERIFICANDO  = 17;
const int PINO_TRAVA_ABERTA = 18;
const int PINO_BLOQUEADO    = 19;
const int PINO_ERROS_C1     = 21;
const int PINO_ERROS_C0     = 22;

// Raiz GTS Root R4 — é quem assina o certificado do Render. Fixamos a raiz, e
// não o certificado do servidor, porque o Render renova o dele a cada três
// meses e a raiz vale até janeiro de 2028. Extraída da cadeia real com:
//   openssl s_client -showcerts -connect lockwise-api.onrender.com:443
const char* RAIZ_GTS_R4 =
  "-----BEGIN CERTIFICATE-----\n"
  "MIIDejCCAmKgAwIBAgIQf+UwvzMTQ77dghYQST2KGzANBgkqhkiG9w0BAQsFADBX\n"
  "MQswCQYDVQQGEwJCRTEZMBcGA1UEChMQR2xvYmFsU2lnbiBudi1zYTEQMA4GA1UE\n"
  "CxMHUm9vdCBDQTEbMBkGA1UEAxMSR2xvYmFsU2lnbiBSb290IENBMB4XDTIzMTEx\n"
  "NTAzNDMyMVoXDTI4MDEyODAwMDA0MlowRzELMAkGA1UEBhMCVVMxIjAgBgNVBAoT\n"
  "GUdvb2dsZSBUcnVzdCBTZXJ2aWNlcyBMTEMxFDASBgNVBAMTC0dUUyBSb290IFI0\n"
  "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAE83Rzp2iLYK5DuDXFgTB7S0md+8Fhzube\n"
  "Rr1r1WEYNa5A3XP3iZEwWus87oV8okB2O6nGuEfYKueSkWpz6bFyOZ8pn6KY019e\n"
  "WIZlD6GEZQbR3IvJx3PIjGov5cSr0R2Ko4H/MIH8MA4GA1UdDwEB/wQEAwIBhjAd\n"
  "BgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwDwYDVR0TAQH/BAUwAwEB/zAd\n"
  "BgNVHQ4EFgQUgEzW63T/STaj1dj8tT7FavCUHYwwHwYDVR0jBBgwFoAUYHtmGkUN\n"
  "l8qJUC99BM00qP/8/UswNgYIKwYBBQUHAQEEKjAoMCYGCCsGAQUFBzAChhpodHRw\n"
  "Oi8vaS5wa2kuZ29vZy9nc3IxLmNydDAtBgNVHR8EJjAkMCKgIKAehhxodHRwOi8v\n"
  "Yy5wa2kuZ29vZy9yL2dzcjEuY3JsMBMGA1UdIAQMMAowCAYGZ4EMAQIBMA0GCSqG\n"
  "SIb3DQEBCwUAA4IBAQAYQrsPBtYDh5bjP2OBDwmkoWhIDDkic574y04tfzHpn+cJ\n"
  "odI2D4SseesQ6bDrarZ7C30ddLibZatoKiws3UL9xnELz4ct92vID24FfVbiI1hY\n"
  "+SW6FoVHkNeWIP0GCbaM4C6uVdF5dTUsMVs/ZbzNnIdCp5Gxmx5ejvEau8otR/Cs\n"
  "kGN+hr/W5GvT1tMBjgWKZ1i4//emhA1JG1BbPzoLJQvyEotc03lXjTaCzv8mEbep\n"
  "8RqZ7a2CPsgRbuvTPBwcOMBBmuFeU88+FSBX6+7iP0il8b4Z0QFqIwwMHfs/L6K1\n"
  "vepuoxtGzi4CZ68zJpiq1UvSqTbFJjtbD4seiMHl\n"
  "-----END CERTIFICATE-----\n";

// ------------------------------------------------------------------ estado

enum Estado { AGUARDANDO, VERIFICANDO, LIBERADO, BLOQUEADO, INDEFINIDO };
const char* NOME_ESTADO[] = { "AGUARDANDO", "VERIFICANDO", "LIBERADO", "BLOQUEADO", "?" };

Estado estadoAnterior = INDEFINIDO;
int contadorAnterior = 0;

WiFiClientSecure tls;

// ------------------------------------------------------------------- setup

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("LOCKWISE — ponte de hardware");

  pinMode(PINO_AGUARDANDO, INPUT);
  pinMode(PINO_VERIFICANDO, INPUT);
  pinMode(PINO_TRAVA_ABERTA, INPUT);
  pinMode(PINO_BLOQUEADO, INPUT);
  pinMode(PINO_ERROS_C1, INPUT);
  pinMode(PINO_ERROS_C0, INPUT);

  conectarWiFi();
  sincronizarRelogio();
  tls.setCACert(RAIZ_GTS_R4);

  // O plano gratuito do Render hiberna. Acordar antes evita que o primeiro
  // acesso do circuito caia num tempo de espera longo — é o mesmo cuidado que
  // o gateway em Python toma (docs/adr/0023).
  acordarAPI();

  estadoAnterior = lerEstado();
  contadorAnterior = lerContador();
  Serial.printf("estado inicial: %s, contador %d\n",
                NOME_ESTADO[estadoAnterior], contadorAnterior);
}

void conectarWiFi() {
  Serial.print("conectando na rede virtual");
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.printf(" conectado, IP %s\n", WiFi.localIP().toString().c_str());
}

// O ESP32 não tem relógio com bateria: ao ligar, acha que é 1970. A API exige
// `momento` em cada evento, e a agregação por hora do modelo de otimização
// depende dele — daí o NTP. No Wokwi isso funciona pelo mesmo gateway virtual
// que leva o HTTPS para fora.
void sincronizarRelogio() {
  Serial.print("sincronizando o relógio");
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");  // 0,0 = trabalhar em UTC
  struct tm agora;
  for (int tentativa = 0; tentativa < 20; tentativa++) {
    if (getLocalTime(&agora, 2000)) {
      char quando[32];
      strftime(quando, sizeof(quando), "%Y-%m-%dT%H:%M:%SZ", &agora);
      Serial.printf(" %s\n", quando);
      return;
    }
    Serial.print(".");
  }
  Serial.println(" falhou — os eventos sairão com data errada");
}

// ISO 8601 em UTC, no formato que a API valida.
String agoraISO() {
  struct tm t;
  if (!getLocalTime(&t, 1000)) return "1970-01-01T00:00:00Z";
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

void acordarAPI() {
  Serial.print("acordando a API");
  for (int tentativa = 0; tentativa < 20; tentativa++) {
    HTTPClient http;
    http.begin(tls, String(API) + "/health");
    http.setTimeout(20000);
    int codigo = http.GET();
    if (codigo == 200) {
      Serial.println(" no ar");
      Serial.println(http.getString());
      http.end();
      return;
    }
    http.end();
    Serial.print(".");
    delay(3000);
  }
  Serial.println(" sem resposta — os eventos podem falhar no começo");
}

// -------------------------------------------------------------- leitura

Estado lerEstado() {
  if (digitalRead(PINO_TRAVA_ABERTA)) return LIBERADO;
  if (digitalRead(PINO_BLOQUEADO))    return BLOQUEADO;
  if (digitalRead(PINO_VERIFICANDO))  return VERIFICANDO;
  if (digitalRead(PINO_AGUARDANDO))   return AGUARDANDO;
  return INDEFINIDO;
}

int lerContador() {
  return (digitalRead(PINO_ERROS_C1) << 1) | digitalRead(PINO_ERROS_C0);
}

// --------------------------------------------------------------- envio

bool postar(const char* rota, const String& corpo) {
  HTTPClient http;
  http.begin(tls, String(API) + rota);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  // O gateway público do Wokwi é lento e o Render pode estar acordando.
  http.setTimeout(20000);

  int codigo = http.POST(corpo);
  if (codigo == 201) {
    Serial.printf("  POST %s -> 201\n", rota);
  } else if (codigo > 0) {
    Serial.printf("  POST %s -> %d  %s\n", rota, codigo, http.getString().c_str());
  } else {
    Serial.printf("  POST %s falhou: %s\n", rota, http.errorToString(codigo).c_str());
  }
  http.end();
  return codigo == 201;
}

void enviarAcesso(const char* resultado, int tentativa, int energiaMj, bool comUsuario) {
  String corpo = "{";
  corpo += "\"momento\":\"" + agoraISO() + "\",";
  corpo += "\"resultado\":\"" + String(resultado) + "\",";
  corpo += "\"tentativa\":" + String(tentativa) + ",";
  corpo += "\"energia_mj\":" + String(energiaMj);
  if (comUsuario) corpo += ",\"usuario_id\":" + String(USUARIO_MORADOR);
  corpo += "}";

  Serial.printf("evento %s tentativa=%d energia_mj=%d\n", resultado, tentativa, energiaMj);
  postar("/acessos", corpo);
}

void enviarAlerta(const char* tipo) {
  Serial.printf("evento ALERTA %s\n", tipo);
  postar("/alertas", "{\"tipo\":\"" + String(tipo) + "\",\"momento\":\"" + agoraISO() + "\"}");
}

// ------------------------------------------------------- transições

// A mesma regra do gateway em Python: evento só nasce em transição de estado,
// nunca por leitura periódica.
void aoMudarEstado(Estado antes, Estado depois, int contadorAgora) {
  Serial.printf("%s -> %s (contador %d)\n",
                NOME_ESTADO[antes], NOME_ESTADO[depois], contadorAgora);

  if (antes == VERIFICANDO && depois == LIBERADO) {
    enviarAcesso("LIBERADO", contadorAnterior + 1, ENERGIA_LIBERACAO_MJ, true);
  } else if (antes == VERIFICANDO && depois == AGUARDANDO) {
    enviarAcesso("NEGADO", contadorAgora, 0, false);
  } else if (antes == VERIFICANDO && depois == BLOQUEADO) {
    enviarAcesso("BLOQUEADO", 3, 0, false);
    enviarAlerta("BLOQUEIO");
  } else if (antes == BLOQUEADO && depois == AGUARDANDO) {
    enviarAlerta("DESBLOQUEIO_ADMIN");
  }
}

// ------------------------------------------------------------------ loop

#if MODO_ENSAIO
// Sem circuito ligado, percorre a sequência do roteiro de demonstração:
// um acesso liberado, três erros, bloqueio e desbloqueio administrativo.
const Estado ENSAIO[] = {
  VERIFICANDO, LIBERADO, AGUARDANDO,              // acesso liberado
  VERIFICANDO, AGUARDANDO,                        // primeiro erro
  VERIFICANDO, AGUARDANDO,                        // segundo erro
  VERIFICANDO, BLOQUEADO,                         // terceiro erro e bloqueio
  AGUARDANDO                                      // RESET do administrador
};
const int CONTADOR_ENSAIO[] = { 0, 0, 0, 0, 1, 1, 2, 2, 3, 0 };
int passoEnsaio = 0;
#endif

void loop() {
#if MODO_ENSAIO
  Estado agora = ENSAIO[passoEnsaio];
  int contadorAgora = CONTADOR_ENSAIO[passoEnsaio];
  passoEnsaio = (passoEnsaio + 1) % (sizeof(ENSAIO) / sizeof(ENSAIO[0]));
  delay(4000);
#else
  Estado agora = lerEstado();
  int contadorAgora = lerContador();
  delay(50);  // amostragem; a transição é que importa, não a frequência
#endif

  if (agora != estadoAnterior && agora != INDEFINIDO) {
    aoMudarEstado(estadoAnterior, agora, contadorAgora);
    estadoAnterior = agora;
  }
  contadorAnterior = contadorAgora;
}
