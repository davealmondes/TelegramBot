"""
jobs.py
-------
Jobs periódicos do bot. O módulo de lembretes foi removido;
este arquivo fica disponível para futuros jobs agendados.
"""
# Nenhum job ativo no momento.
# Para adicionar um job: defina uma coroutine async def meu_job(context) -> None
# e registre em main.py com application.job_queue.run_repeating(...).