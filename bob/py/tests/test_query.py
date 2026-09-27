import unittest

from davidkhala.data.base.sqlite import SQLite

from davidkhala.ibm.bob import db_path, get_tasks, messages


class TestQuery(unittest.TestCase):

    def test_tasks(self):
        with SQLite(str(db_path)) as db:
            tasks = get_tasks(db)

            print(f"\nTotal tasks: {len(tasks)}")
            print()

            for i, t in enumerate(tasks):
                cost_str = f"${t['cost']:.4f}" if t["cost"] else "$0"
                title_display = (t["title"] or t["first_message"] or "(no title)")[:70]
                print(
                    f"[{i+1:3}] {t['created']}  {t['status']:8}  {cost_str:10}  {title_display}"
                )
                print(
                    f"       id={t['id']}  workspace={t['workspace']}  mode={t['mode']}"
                )

            self.assertGreater(len(tasks), 0)

    def test_messages(self):
        with SQLite(str(db_path)) as db:
            print(messages(db))


if __name__ == "__main__":
    unittest.main()
