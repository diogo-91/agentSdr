---
description: como commitar e enviar alterações para o GitHub (PowerShell)
---

Sempre que uma atualização de código for feita no projeto, execute os passos abaixo para salvar e publicar as mudanças no GitHub.

1. Verificar o status atual para ver o que mudou:
```powershell
git status
```

// turbo
2. Adicionar todos os arquivos modificados:
```powershell
git add -A
```

3. Fazer o commit com uma mensagem descritiva (substituir `[mensagem]` pelo contexto da mudança):
```powershell
git commit -m "[tipo]: [mensagem curta descrevendo a mudança]"
```
Exemplos de tipos: `fix`, `feat`, `refactor`, `docs`, `chore`

// turbo
4. Enviar para o GitHub:
```powershell
git push origin main
```

> **Nota:** Use `;` para encadear comandos no PowerShell (não `&&`).
> Exemplo completo: `git add -A; git commit -m "fix: descrição"; git push origin main`
