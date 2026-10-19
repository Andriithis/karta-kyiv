"""Е25: повні тексти рішень для читання прикладів очима (ZAVDANNYA-38, 2).

Локально повних текстів немає (архів — артефакт проходу), тож беремо
сторінку рішення в реєстрі тим самим шляхом, що й прохід по текстах
(step1c_teksty.review_text). Кешуємо в kod/e25_vyhid/teksty/ (не в git).

Запуск: py -3 e25_teksty.py <doc_id> [<doc_id> ...]  — друкує початок тексту
від «ВСТАНОВИВ» / «встановив» (1500 знаків).
"""
import os, re, sys, time
K = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(K, '..', '..', '..', 'src')))
import step1c_teksty as TK
KESH = os.path.join(K, 'e25_vyhid', 'teksty')


def tekst(d):
    os.makedirs(KESH, exist_ok=True)
    f = os.path.join(KESH, d + '.txt')
    if os.path.exists(f): return open(f, encoding='utf-8').read()
    t = TK.review_text(d) or ''
    open(f, 'w', encoding='utf-8').write(t)
    time.sleep(1)
    return t


if __name__ == '__main__':
    n = int(os.environ.get('N', '1500'))
    for d in sys.argv[1:]:
        t = re.sub(r'\s+', ' ', tekst(d))
        m = re.search(r'встанови\w*', t, re.I)
        print(f'==== {d} ({len(t)} знаків)\n{t[(m.start() if m else 0):][:n]}\n')
