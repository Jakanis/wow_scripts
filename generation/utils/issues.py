import csv
import os
import sys
from dataclasses import dataclass, replace

ERROR = 'error'
WARNING = 'warning'
NOTE = 'note'

_SEVERITY_ORDER = {ERROR: 0, WARNING: 1, NOTE: 2}
_COLUMNS = ('severity', 'rule', 'entity', 'id', 'expansion', 'field', 'message', 'note')


@dataclass(frozen=True)
class Issue:
    severity: str
    rule: str
    entity: str
    id: str = ''
    expansion: str = ''
    field: str = ''
    message: str = ''

    def where(self) -> str:
        at = f'{self.entity}#{self.id}' if self.id != '' else self.entity
        if self.expansion:
            at += f':{self.expansion}'
        return f'{at} {self.field}'.rstrip()

    def __str__(self) -> str:
        return f'[{self.severity}] {self.rule} {self.where()}: {self.message}'


class IssueLog:
    """
    Collects issues instead of printing them, compares the run against the
    module's verified_issues.tsv and decides the exit code.

    The whole record is the identity, message included, so any change in what a
    check says is a reason to look at it again.

    A generator module keeps one at module level and calls it from anywhere in
    the file, rather than passing it down:

        log = IssueLog('spells')
    """

    def __init__(self, module: str, verified_path: str = 'verified_issues.tsv'):
        self.module = module
        self.verified_path = verified_path
        self.issues: list[Issue] = []
        self.failed = False

    def add(self, severity: str, rule: str, entity: str, message: str,
            id='', expansion: str = '', field: str = '') -> None:
        self.issues.append(Issue(severity, rule, entity, str(id), expansion, field, message))

    def error(self, rule, entity, message, **kw):
        self.add(ERROR, rule, entity, message, **kw)

    def warning(self, rule, entity, message, **kw):
        self.add(WARNING, rule, entity, message, **kw)

    def note(self, rule, entity, message, **kw):
        self.add(NOTE, rule, entity, message, **kw)

    def clear(self) -> None:
        self.issues.clear()
        self.failed = False

    def fail(self, reason: str) -> None:
        # the run itself could not finish: a download that did not complete, a
        # source that could not be parsed
        self.failed = True
        self.error('run-failed', self.module, reason)

    # -- verified file ----------------------------------------------------

    def load_verified(self) -> dict[Issue, str]:
        if not os.path.exists(self.verified_path):
            return {}
        out = {}
        with open(self.verified_path, encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                issue = Issue(row['severity'], row['rule'], row['entity'], row['id'],
                              row['expansion'], row['field'], row['message'] or '')
                out[issue] = row.get('note') or ''
            return out

    def write_verified(self, accepted: dict[Issue, str]) -> None:
        rows = sorted(accepted.items(),
                      key=lambda kv: (_SEVERITY_ORDER.get(kv[0].severity, 9), kv[0].rule,
                                      kv[0].entity, str(kv[0].id).zfill(12), kv[0].expansion,
                                      kv[0].field))
        os.makedirs(os.path.dirname(self.verified_path) or '.', exist_ok=True)
        with open(self.verified_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerow(_COLUMNS)
            for issue, note in rows:
                writer.writerow([issue.severity, issue.rule, issue.entity, issue.id,
                                 issue.expansion, issue.field, issue.message, note])

    def accept_new(self, note: str = '') -> int:
        verified = self.load_verified()
        new, _, _ = self.compare()
        for issue in new:
            verified[issue] = note
        self.write_verified(verified)
        return len(new)

    # -- comparison -------------------------------------------------------

    def compare(self) -> tuple[list[Issue], list[Issue], list[Issue]]:
        verified = self.load_verified()
        current = set(self.issues)
        new = [i for i in self.issues if i not in verified]
        known = [i for i in self.issues if i in verified]
        gone = [i for i in verified if i not in current]
        return new, known, gone

    @staticmethod
    def _pair_changed(new: list[Issue], gone: list[Issue]):
        # a reworded message leaves the old identity and creates a new one, so
        # show the pair together instead of as two unrelated lines
        def place(issue):
            return issue.rule, issue.entity, issue.id, issue.expansion, issue.field

        gone_by_place = {}
        for issue in gone:
            gone_by_place.setdefault(place(issue), []).append(issue)

        changed, rest_new = [], []
        for issue in new:
            candidates = gone_by_place.get(place(issue))
            if candidates:
                changed.append((candidates.pop(0), issue))
            else:
                rest_new.append(issue)
        rest_gone = [i for group in gone_by_place.values() for i in group]
        return changed, rest_new, rest_gone

    # -- output -----------------------------------------------------------

    @staticmethod
    def _indent(text: str, pad: str) -> str:
        return text.replace('\n', '\n' + pad)

    @classmethod
    def _block(cls, head: str, text: str, pad: str) -> str:
        # a multiline message starts on its own line, so all of its lines share an indent
        if '\n' in text:
            return head + '\n' + pad + cls._indent(text, pad)
        return f'{head} {text}'

    @classmethod
    def _render(cls, issue: Issue, pad: str) -> str:
        return cls._block(f'{pad}[{issue.severity}] {issue.rule} {issue.where()}:',
                          issue.message, pad + '  ')

    def report(self) -> None:
        new, known, gone = self.compare()
        changed, new, gone = self._pair_changed(new, gone)

        print('-' * 100)
        print(f'{self.module}: {len(self.issues)} issue(s) -> {len(new)} new, '
              f'{len(changed)} changed, {len(known)} known; '
              f'{len(gone)} verified entr(ies) no longer occur')

        if new:
            print('\nNEW')
            for issue in sorted(new, key=lambda i: (_SEVERITY_ORDER.get(i.severity, 9), i.rule)):
                print(self._render(issue, '  '))
        if changed:
            print('\nCHANGED (accepted earlier, the message is different now)')
            for before, after in changed:
                print(f'  {after.where()}  {after.rule}')
                for label, text in (('was', before.message), ('now', after.message)):
                    print(self._block(f'    {label}:', text, '      '))
        if gone:
            print(f'\nNO LONGER OCCURS (drop from {self.verified_path})')
            for issue in gone:
                print(self._render(issue, '  '))

    def write(self, path: str = 'output/issues.tsv') -> None:
        new, known, gone = self.compare()
        state = {}
        state.update({i: 'new' for i in new})
        state.update({i: 'known' for i in known})
        state.update({i: 'gone' for i in gone})
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerow(('state',) + _COLUMNS[:-1])
            for issue, bucket in state.items():
                writer.writerow([bucket, issue.severity, issue.rule, issue.entity, issue.id,
                                 issue.expansion, issue.field, issue.message])

    def exit_code(self, strict: bool = False) -> int:
        if self.failed:
            return 2
        new, _, gone = self.compare()
        if any(i.severity == ERROR for i in new):
            return 1
        if strict and (new or gone):
            return 1
        return 0

    def finish(self, strict: bool = False, write_to: str = 'output/issues.tsv') -> int:
        self.report()
        self.write(write_to)
        return self.exit_code(strict)


def run(main, module: str, strict: bool = False) -> None:
    """Wraps a module's main() so an unhandled failure exits 2, not 0."""
    log = IssueLog(module)
    try:
        result = main(log)
    except Exception as exc:
        log.fail(f'{type(exc).__name__}: {exc}')
        log.report()
        raise SystemExit(2) from exc
    raise SystemExit(result if isinstance(result, int) else log.finish(strict))
