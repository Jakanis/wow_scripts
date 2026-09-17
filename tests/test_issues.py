import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generation.utils.issues import IssueLog


def make_log():
    path = os.path.join(tempfile.mkdtemp(), 'verified_issues.tsv')
    return IssueLog('test', path)


def check(name, got, want):
    if got == want:
        return 0
    print(f'FAIL {name}\n     expected {want}\n     got      {got}')
    return 1


def main() -> int:
    failures = 0

    # nothing verified yet: everything is new
    log = make_log()
    log.warning('redundant-translation', 'item', 'needs spell#3607', id=3912,
                expansion='classic', field='effect#0')
    log.error('missing-ref', 'item', 'no spell', id=1, expansion='tbc')
    new, known, gone = log.compare()
    failures += check('all new', (len(new), len(known), len(gone)), (2, 0, 0))
    failures += check('new error fails', log.exit_code(), 1)

    # accept them, then the same run is quiet and passes
    log.accept_new('checked by hand')
    new, known, gone = log.compare()
    failures += check('all known', (len(new), len(known), len(gone)), (0, 2, 0))
    failures += check('known passes', log.exit_code(), 0)
    failures += check('note kept', list(log.load_verified().values())[0], 'checked by hand')

    # a selective accept files only what the predicate lets through
    partial = make_log()
    partial.warning('rule-a', 'item', 'one', id=1)
    partial.warning('rule-b', 'item', 'two', id=2)
    accepted = partial.accept_new('only a', only=lambda issue: issue.rule == 'rule-a')
    new, known, gone = partial.compare()
    failures += check('selective accept', (accepted, len(new), len(known)), (1, 1, 1))

    # a reworded message is a new identity plus a gone one, paired as changed
    reworded = IssueLog('test', log.verified_path)
    reworded.warning('redundant-translation', 'item', 'needs spell#9999', id=3912,
                     expansion='classic', field='effect#0')
    reworded.error('missing-ref', 'item', 'no spell', id=1, expansion='tbc')
    new, known, gone = reworded.compare()
    changed, rest_new, rest_gone = reworded._pair_changed(new, gone)
    failures += check('reworded pairs up', (len(changed), len(rest_new), len(rest_gone)), (1, 0, 0))
    failures += check('reworded warning does not fail', reworded.exit_code(), 0)
    failures += check('strict fails on it', reworded.exit_code(strict=True), 1)

    # a warning that stopped happening
    fixed = IssueLog('test', log.verified_path)
    fixed.error('missing-ref', 'item', 'no spell', id=1, expansion='tbc')
    new, known, gone = fixed.compare()
    failures += check('one gone', (len(new), len(known), len(gone)), (0, 1, 1))
    failures += check('gone alone passes', fixed.exit_code(), 0)

    # multi-line messages survive the round trip
    multi = make_log()
    multi.warning('original-differs', 'spell', 'differs:\n- old text\n+ new text',
                  id=1231417, expansion='sod', field='description')
    multi.accept_new()
    failures += check('multiline round trip', len(multi.compare()[1]), 1)

    # a failed run beats everything
    broken = make_log()
    broken.fail('download did not complete')
    failures += check('failed run exits 2', broken.exit_code(), 2)

    print(f'\n{7 - failures}/7 checks pass' if failures else '\nall checks pass')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
