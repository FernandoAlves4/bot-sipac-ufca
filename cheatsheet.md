# 🎯 Cheatsheet — Bot SIPAC UFCA

Referência rápida de comandos para o projeto.

---

## 🖥️ VM Oracle Cloud (PRODUÇÃO)

**O bot roda aqui, 24/7.**

### Acesso

```bash
ssh oci-danilo
```

### Comandos do systemd (na VM)

| Comando | O que faz |
|---|---|
| `sudo systemctl status bot-sipac` | Ver se está rodando |
| `sudo systemctl restart bot-sipac` | Reiniciar |
| `sudo systemctl stop bot-sipac` | Parar |
| `sudo systemctl start bot-sipac` | Iniciar |
| `sudo journalctl -u bot-sipac -n 50` | Ver últimos logs |
| `sudo journalctl -u bot-sipac -f` | Ver logs em tempo real |

### Atualizar a base (na VM)

```bash
cd ~/bot-sipac-ufca
source venv/bin/activate
~/bot-sipac-ufca/atualizar_base.sh
```

### Informações da VM

- **Hostname:** vnic-avanci
- **Usuário:** nando
- **Projeto:** /home/nando/bot-sipac-ufca

---

## 💻 PC (DESENVOLVIMENTO)

- **Pasta:** `/home/fernando/bot_sipac`
- **Status:** ❌ Bot parado (migrado pra VM)

### Enviar mudanças pro GitHub

```bash
cd ~/bot_sipac
git add .
git commit -m "Descrição da mudança"
git push
```

### Puxar mudanças da VM

```bash
cd ~/bot_sipac
git pull
```

---

## 🤖 Comandos do bot no Telegram

| Comando | O que faz |
|---|---|
| `/start` | Boas-vindas |
| `/ajuda` | Exemplos de perguntas |
| `/exemplos` | Mais exemplos |
| `/status` | Painel de estatísticas |
| `/historico` | Ver o que você já perguntou |
| `/limpar` | Apagar histórico |
| `/feedback` | Enviar sugestão |

