import unittest

from app.db import mentira_percent
from app.factcheck import (
    attach_citations,
    citation_sources,
    is_agency_url,
    parse_json,
    sanitize_verdict,
)
from app.ie_mcp import format_context
from app.listener import explain_audio_error, resolve_stream, youtube_cookie_text


class VerdictTests(unittest.TestCase):
    def test_percentual_de_mentira(self):
        self.assertIsNone(mentira_percent({}))
        self.assertIsNone(mentira_percent({"sem_evidencia": 4}))
        self.assertEqual(
            mentira_percent({"contradito": 1, "sustentado": 1, "exagerado": 2}),
            25.0,
        )

    def test_sem_fonte_nao_contradiz(self):
        verdict = sanitize_verdict(
            {"status": "contradito", "confidence": 0.9, "summary": "não achei", "sources": []}
        )
        self.assertEqual(verdict["status"], "sem_evidencia")

    def test_fonte_https_permanece(self):
        verdict = sanitize_verdict(
            {
                "status": "sustentado",
                "confidence": 2,
                "sources": [{"url": "https://www.ibge.gov.br/x", "title": "IBGE", "note": "tabela"}],
            }
        )
        self.assertEqual(verdict["status"], "sustentado")
        self.assertEqual(verdict["confidence"], 0.65)
        self.assertEqual(verdict["sources"][0]["title"], "IBGE")
        self.assertEqual(verdict["sources"][0]["kind"], "oficial")
        self.assertEqual(verdict["sources"][0]["excerpt"], "tabela")
        self.assertEqual(verdict["theme"], "outro")

    def test_carimbo_novo_sem_https_cai(self):
        verdict = sanitize_verdict(
            {"status": "distorcido", "theme": "saude", "sources": [{"url": "http://exemplo.com"}]}
        )
        self.assertEqual(verdict["status"], "sem_evidencia")

    def test_promessa_nao_exige_fonte(self):
        verdict = sanitize_verdict({"status": "promessa", "summary": "compromisso", "sources": []})
        self.assertEqual(verdict["status"], "promessa")

    def test_segunda_leitura_discordante(self):
        from app.factcheck import stamps_conflict

        self.assertTrue(stamps_conflict("sustentado", "contradito"))
        self.assertFalse(stamps_conflict("sustentado", "sustentado_ressalva"))
        self.assertFalse(stamps_conflict("sustentado", "sem_evidencia"))

    def test_tipo_de_fonte(self):
        from app.factcheck import source_kind

        self.assertEqual(source_kind("https://www.aosfatos.org/noticia/x"), "checagem")
        self.assertEqual(source_kind("https://www1.folha.uol.com.br/poder/x"), "imprensa")

    def test_http_nao_conta(self):
        verdict = sanitize_verdict(
            {"status": "exagerado", "sources": [{"url": "http://example.com"}]}
        )
        self.assertEqual(verdict["status"], "sem_evidencia")

    def test_citacao_da_busca_entra_como_fonte(self):
        payload = {
            "citations": ["https://www.ibge.gov.br/tabela"],
            "choices": [
                {
                    "message": {
                        "annotations": [
                            {"url_citation": {"url": "https://www.gov.br/inep/nota"}}
                        ]
                    }
                }
            ],
        }
        verdict = sanitize_verdict(
            attach_citations(
                {"status": "sustentado", "confidence": 0.7, "sources": []},
                citation_sources(payload),
            )
        )
        self.assertEqual(verdict["status"], "sustentado")
        self.assertEqual(len(verdict["sources"]), 2)

    def test_json_com_cerca(self):
        self.assertEqual(parse_json('```json\n{"claims":[]}\n```')["claims"], [])

    def test_url_de_agencia(self):
        self.assertTrue(is_agency_url("https://www.aosfatos.org/noticias/debate-band/"))
        self.assertTrue(is_agency_url("https://g1.globo.com/fato-ou-fake/noticia/x"))
        self.assertFalse(is_agency_url("https://www.estadao.com.br/politica/"))
        self.assertTrue(is_agency_url("https://www.estadao.com.br/estadao-verifica/checagem/"))

    def test_contexto_ie_vazio(self):
        text = format_context({"enabled": True, "itens": []})
        self.assertEqual(text, "")

    def test_erro_de_robo_sem_cookie(self):
        message = explain_audio_error("Sign in to confirm you're not a bot")
        self.assertIn("BandNews FM SP", message)

    def test_erro_de_robo_com_cookie(self):
        message = explain_audio_error("Sign in to confirm you're not a bot", has_cookies=True)
        self.assertIn("BandNews FM SP", message)

    def test_filtra_so_youtube(self):
        raw = "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".paypal.com\tTRUE\t/\tTRUE\t1\tsegredo\tabc",
                ".youtube.com\tTRUE\t/\tTRUE\t1\tLOGIN_INFO\tabc",
            ]
        )
        kept = youtube_cookie_text(raw)
        self.assertIn("youtube.com", kept)
        self.assertNotIn("paypal.com", kept)

    def test_aceita_quebra_escapada(self):
        raw = ".youtube.com\\tTRUE\\t/\\tTRUE\\t1\\tPREF\\tok\\n.google.com\\tTRUE\\t/\\tTRUE\\t1\\tSID\\tok"
        kept = youtube_cookie_text(raw)
        self.assertIn("PREF", kept)
        self.assertNotIn("google.com", kept)

    def test_aceita_bandnews_e_youtube(self):
        self.assertIn("BANDNEWSFM", resolve_stream("bandnews_sp"))
        self.assertIn("CBN_SPAAC", resolve_stream("cbn_sp"))
        self.assertIn("youtube.com", resolve_stream("https://www.youtube.com/watch?v=Gqc1rQtzWUk"))
        with self.assertRaises(ValueError):
            resolve_stream("https://evil.example/audio")

    def test_globoplay_pede_a_aba(self):
        with self.assertRaises(ValueError) as caught:
            resolve_stream("https://globoplay.globo.com/ao-vivo/globo")
        self.assertIn("aba", str(caught.exception).casefold())


if __name__ == "__main__":
    unittest.main()
