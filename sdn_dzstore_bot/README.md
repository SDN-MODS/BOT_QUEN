# SDN_DZSTORE_BOT

Sistema profissional de loja virtual para Discord, desenvolvido para servidores de DayZ PC.

## 🎯 Funcionalidades

- **👤 Sistema de Contas**: Cadastro de jogadores com vinculação Discord ↔ Steam
- **💰 Carteira Virtual**: Sistema de Coins com transações registradas
- **🛒 Loja Completa**: Produtos organizados por categorias
- **🛍️ Carrinho de Compras**: Adicione múltiplos produtos e finalize junto
- **📦 Pedidos**: Histórico completo de compras com status
- **🎟️ Cupons**: Sistema de descontos e promoções
- **🔐 Painel Administrativo**: Gestão completa da loja
- **📜 Logs e Auditoria**: Todas as ações administrativas registradas

## 🚀 Instalação

### Pré-requisitos

- Python 3.9+
- Discord Bot Token
- SQLite (já incluso no Python)

### Passos

1. Clone o repositório ou baixe os arquivos

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o bot:
   - Copie `config/.env.example` para `config/.env`
   - Edite `config/.env` com suas credenciais:
```env
DISCORD_TOKEN=seu_token_aqui
CLIENT_ID=seu_client_id
GUILD_ID=seu_guild_id
```

4. Execute o bot:
```bash
python main.py
```

## 📁 Estrutura do Projeto

```
sdn_dzstore_bot/
├── config/              # Configurações do bot
│   ├── config.json      # Configurações em JSON
│   └── .env             # Variáveis de ambiente
├── database/            # Gerenciamento do banco de dados
├── services/            # Lógica de negócios
│   ├── player_service.py    # Jogadores e transações
│   ├── product_service.py   # Produtos e categorias
│   ├── order_service.py     # Pedidos e carrinho
│   └── log_service.py       # Logs e auditoria
├── interfaces/          # Interfaces Discord
│   ├── discord_ui.py        # Componentes UI reutilizáveis
│   ├── account_interface.py # Interface de conta
│   ├── store_interface.py   # Interface da loja
│   ├── cart_interface.py    # Interface do carrinho
│   ├── orders_interface.py  # Interface de pedidos
│   ├── coins_interface.py   # Interface de coins
│   └── admin_interface.py   # Painel administrativo
├── handlers/            # Handlers de eventos
├── commands/            # Comandos do bot
├── utils/               # Utilitários
├── main.py              # Ponto de entrada principal
└── requirements.txt     # Dependências
```

## 💿 Banco de Dados

O sistema utiliza SQLite com as seguintes tabelas:

- `players` - Jogadores cadastrados
- `coin_transactions` - Transações de Coins
- `coin_packages` - Pacotes de Coins disponíveis
- `categories` - Categorias de produtos
- `products` - Produtos da loja
- `cart_items` - Itens no carrinho
- `orders` - Pedidos realizados
- `order_items` - Itens dos pedidos
- `coupons` - Cupons de desconto
- `payments` - Pagamentos
- `admin_logs` - Logs administrativos
- `settings` - Configurações do sistema

## 🎮 Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `/loja` | Abrir a loja virtual |
| `/conta` | Gerenciar sua conta |
| `/coins` | Comprar Coins |
| `/pedidos` | Ver seus pedidos |
| `/carrinho` | Ver seu carrinho |
| `/ajuda` | Central de ajuda |
| `/admin` | Painel administrativo |

## 🔧 Configuração

Edite `config/config.json` para personalizar:

- Nome da loja
- Cores dos embeds
- Canais de logs
- Cargos administrativos
- Configurações de API (para integração futura com DayZ)

## 🔐 Segurança

- Validação de Steam ID único
- Proteção contra saldo negativo
- Registro de todas as transações
- Logs de ações administrativas
- Controle de permissões por cargo

## 📈 Preparado para Expansão

A arquitetura foi desenvolvida para permitir futuras integrações:

- API REST para integração com servidor DayZ
- Sistema VIP e assinaturas
- Transferência de Coins entre jogadores
- Gift Cards
- Dashboard Web
- Relatórios financeiros

## 📝 Licença

Este projeto é proprietário e destinado ao uso no servidor SDN DayZ.

---

**SDN_DZSTORE_BOT** - Sistema profissional de loja virtual para DayZ
