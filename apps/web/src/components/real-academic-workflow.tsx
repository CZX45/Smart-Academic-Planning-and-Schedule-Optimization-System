"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchAcademicWorkflow,
  createDegreeAudit,
  fetchDegreeAuditRequirements,
  createCourseEligibilityCheck,
  createAcademicPlan,
  fetchStudentAcademicPlans,
  fetchAcademicPlan,
  compareAcademicPlans,
  createAcademicScenario,
  fetchStudentAcademicScenarios,
  fetchAcademicScenarioComparison,
  createScheduleOptimization,
  fetchStudentScheduleOptimizations,
  fetchScheduleOptimization,
  type AcademicWorkflow,
  type DegreeAuditRun,
  type RequirementEvaluation,
  type CourseEligibilityCheck,
  type AcademicPlanDetail,
  type AcademicPlanComparison,
  type ScenarioComparisonSnapshot,
  type ScheduleOptimizationDetail,
} from "@sapsos/shared";
import { useScopedWorkflowState } from "../lib/use-scoped-workflow-state";
import { localizeStatusLabel as statusLabel } from "../lib/zh-cn";

type Results = {
  busy?: boolean;
  message?: string;
  audit?: DegreeAuditRun;
  requirements?: RequirementEvaluation[];
  eligibility?: CourseEligibilityCheck;
  plan?: AcademicPlanDetail;
  comparison?: AcademicPlanComparison[];
  scenario?: ScenarioComparisonSnapshot;
  schedule?: ScheduleOptimizationDetail;
};

export function RealAcademicWorkflow({
  apiBaseUrl,
  studentId,
  refreshKey,
}: {
  apiBaseUrl: string;
  studentId: string;
  refreshKey: string;
}) {
  const [reload, setReload] = useState(0);
  const scope = JSON.stringify([apiBaseUrl, studentId, refreshKey, reload]);
  const [state, setState] = useScopedWorkflowState<{
    data?: AcademicWorkflow;
    error?: string;
  }>(scope, {});
  useEffect(() => {
    let active = true;
    void fetchAcademicWorkflow(apiBaseUrl, studentId, { timeoutMs: 8000 })
      .then((data) => {
        if (active) setState({ data });
      })
      .catch(() => {
        if (active)
          setState({
            error: "读取已审核数据失败，请确认本地服务已启动后重试。",
          });
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, studentId, scope, setState]);
  return (
    <section aria-label="真实学生学业工作流">
      <h2>已审核的学业数据</h2>
      <button type="button" onClick={() => setReload((value) => value + 1)}>
        刷新已应用数据
      </button>
      {!state.data && !state.error ? (
        <p role="status">正在加载当前学生的课程、培养方案和学期…</p>
      ) : null}
      {state.error ? <p role="alert">{state.error}</p> : null}
      {state.data ? (
        <RealWorkflowInputs
          key={`${scope}:${state.data.revision}`}
          data={state.data}
          apiBaseUrl={apiBaseUrl}
        />
      ) : null}
    </section>
  );
}

function RealWorkflowInputs({
  data,
  apiBaseUrl,
}: {
  data: AcademicWorkflow;
  apiBaseUrl: string;
}) {
  const [programId, setProgramId] = useState(
    data.programs.length === 1 ? data.programs[0].id : "",
  );
  const [termId, setTermId] = useState("");
  const [courseId, setCourseId] = useState("");
  const [courseIds, setCourseIds] = useState<string[]>([]);
  const [minimum, setMinimum] = useState(0);
  const [preferred, setPreferred] = useState(12);
  const [maximum, setMaximum] = useState(18);
  const [horizon, setHorizon] = useState(4);
  const [noFriday, setNoFriday] = useState(false);
  const scope = JSON.stringify([
    data.revision,
    programId,
    termId,
    courseId,
    courseIds,
    minimum,
    preferred,
    maximum,
    horizon,
    noFriday,
  ]);
  const [results, setResults] = useScopedWorkflowState<Results>(scope, {});
  const running = useRef(false);
  const program = data.programs.find((item) => item.id === programId);
  const creditPolicyValid =
    Number.isFinite(minimum) &&
    minimum >= 0 &&
    minimum <= preferred &&
    preferred <= maximum;
  async function run(action: () => Promise<Partial<Results>>) {
    if (running.current) return;
    running.current = true;
    setResults((current) => ({ ...current, busy: true, message: undefined }));
    try {
      const next = await action();
      setResults((current) => ({ ...current, ...next, busy: false }));
    } catch {
      setResults((current) => ({
        ...current,
        busy: false,
        message:
          "计算或读取未完成。请核对课程历史、专业规则、学期及学分范围，完成缺失审核后重试。",
      }));
    } finally {
      running.current = false;
    }
  }
  const student = { student_profile_id: data.student_profile_id };
  return (
    <>
      {data.issues.length ? (
        <div role="status">
          <h3>需要核对的数据</h3>
          {[...new Set(data.issues.map((item) => item.reason_code))].map(
            (code) => (
              <details key={code} open>
                <summary>
                  {
                    data.issues.find((item) => item.reason_code === code)
                      ?.message
                  }
                  （
                  {
                    data.issues.filter((item) => item.reason_code === code)
                      .length
                  }{" "}
                  项）
                </summary>
                <ul>
                  {data.issues
                    .filter((item) => item.reason_code === code)
                    .map((item, index) => (
                      <li key={index}>
                        {item.message}{" "}
                        {item.evidence_reference ? (
                          <span>来源：{item.evidence_reference}</span>
                        ) : null}
                      </li>
                    ))}
                </ul>
              </details>
            ),
          )}
          <a href="#data-review">进入人工审核</a>
        </div>
      ) : null}
      <div className="scenario-controls">
        <label>
          已审核专业与 Catalog 年份
          <select
            value={programId}
            onChange={(event) => setProgramId(event.target.value)}
          >
            <option value="">请选择已审核培养方案</option>
            {data.programs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.catalog_year}
              </option>
            ))}
          </select>
        </label>
        <label>
          真实学期
          <select
            value={termId}
            onChange={(event) => setTermId(event.target.value)}
          >
            <option value="">请选择来源明确的学期</option>
            {data.terms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code}（{item.starts_on} 至 {item.ends_on}）
              </option>
            ))}
          </select>
        </label>
        <label>
          已应用课程
          <select
            value={courseId}
            onChange={(event) => setCourseId(event.target.value)}
          >
            <option value="">请选择课程</option>
            {data.courses.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} · {item.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      {program ? (
        <p>
          培养方案来源：{program.source.source_reference}；Catalog：
          {program.catalog_year}。审核确认不代表学校官方认证。
        </p>
      ) : null}
      <section aria-label="已应用课程目录">
        <h3>课程目录</h3>
        <ul>
          {data.courses.map((item) => (
            <li key={item.id}>
              {item.code} · {item.title} · {item.credits} 学分；来源：
              {item.source.source_reference ?? "未提供"}；读取时间：
              {item.source.source_retrieved_at ?? "未知"}
            </li>
          ))}
        </ul>
      </section>
      {results.busy ? <p role="status">处理中…</p> : null}
      {results.message ? <p role="alert">{results.message}</p> : null}
      <section id="degree-audit">
        <h3>学业审核</h3>
        <p>
          已完成学分来自已修读证据；在修和已计划学分仅表示潜在贡献。剩余学分和要求满足情况分别核对，不能据此自动确认毕业。
        </p>
        <button
          disabled={!program || results.busy}
          onClick={() =>
            void run(async () => {
              const audit = await createDegreeAudit(apiBaseUrl, {
                ...student,
                program_version_id: programId,
                calculation_mode: "CURRENT",
              });
              return {
                audit,
                requirements: await fetchDegreeAuditRequirements(
                  apiBaseUrl,
                  audit.id,
                ),
              };
            })
          }
        >
          计算真实学业审核
        </button>
        {results.audit ? (
          <>
            <p>
              已完成 {results.audit.completed_credits} · 在修{" "}
              {results.audit.in_progress_credits} · 已计划{" "}
              {results.audit.planned_credits} · 剩余{" "}
              {results.audit.remaining_credits}
            </p>
            <p>
              规则来源：{results.audit.rule_source_reference ?? "待审核"}
              ；Catalog：{results.audit.rule_catalog_year ?? "未知"}；核实状态：
              {statusLabel(results.audit.rule_resolution_state)}
            </p>
            <ul>
              {results.requirements?.map((item) => (
                <li key={item.id}>
                  {item.requirement_name}（{item.requirement_code}）·{" "}
                  {statusLabel(item.status)} · 应用 {item.satisfied_credits}{" "}
                  学分。{item.explanation}
                  <p>
                    来源：{item.requirement_source ?? "待审核"}；Catalog：
                    {item.catalog_version ?? "未知"}；原因：
                    {item.reason_code ?? "未提供"}；核实状态：
                    {statusLabel(item.verification_state)}
                  </p>
                  <ul>
                    {item.applications.map((application) => (
                      <li key={application.id}>
                        {application.explanation} · {application.credit_amount}{" "}
                        学分
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
      <section id="eligibility">
        <h3>课程资格</h3>
        <button
          disabled={!courseId || !termId || results.busy}
          onClick={() =>
            void run(async () => ({
              eligibility: await createCourseEligibilityCheck(apiBaseUrl, {
                ...student,
                course_id: courseId,
                target_term_id: termId,
                mode: "PROJECTED",
              }),
            }))
          }
        >
          检查真实课程资格
        </button>
        {results.eligibility ? (
          <>
            <p>{statusLabel(results.eligibility.overall_result)}</p>
            <ul>
              {results.eligibility.warnings.map((item) => (
                <li key={item.id}>{item.message}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
      <fieldset>
        <legend>规划学分范围</legend>
        <label>
          最低学分
          <input
            type="number"
            min={0}
            value={minimum}
            onChange={(event) => setMinimum(event.target.valueAsNumber)}
          />
        </label>
        <label>
          期望学分
          <input
            type="number"
            min={0}
            value={preferred}
            onChange={(event) => setPreferred(event.target.valueAsNumber)}
          />
        </label>
        <label>
          最高学分
          <input
            type="number"
            min={0}
            value={maximum}
            onChange={(event) => setMaximum(event.target.valueAsNumber)}
          />
        </label>
        <label>
          规划学期数
          <input
            type="number"
            min={1}
            max={16}
            value={horizon}
            onChange={(event) => setHorizon(event.target.valueAsNumber)}
          />
        </label>
        {!creditPolicyValid ? (
          <p role="alert">请确保 0 ≤ 最低学分 ≤ 期望学分 ≤ 最高学分。</p>
        ) : null}
      </fieldset>
      <section id="academic-plan">
        <h3>长期规划</h3>
        <p>
          建议安排需核实开课情况；未知或未审核的开课信息不会成为确定开课承诺。
        </p>
        <button
          disabled={
            !program ||
            !termId ||
            !creditPolicyValid ||
            !Number.isInteger(horizon) ||
            horizon < 1 ||
            horizon > 16 ||
            results.busy
          }
          onClick={() =>
            void run(async () => ({
              plan: await createAcademicPlan(apiBaseUrl, {
                ...student,
                program_version_id: programId,
                planning_mode: "CURRENT_PROGRAM",
                start_term_id: termId,
                terms_to_plan: horizon,
                minimum_credits_per_term: minimum,
                maximum_credits_per_term: maximum,
                preferred_credits_per_term: preferred,
              }),
            }))
          }
        >
          生成真实长期规划
        </button>
        <button
          disabled={results.busy}
          onClick={() =>
            void run(async () => {
              const plans = await fetchStudentAcademicPlans(
                apiBaseUrl,
                data.student_profile_id,
              );
              const selected = plans.find(
                (item) => item.program_version_id === programId,
              );
              return selected
                ? { plan: await fetchAcademicPlan(apiBaseUrl, selected.id) }
                : { message: "当前培养方案尚无已保存规划。" };
            })
          }
        >
          读取已保存规划
        </button>
        <button
          disabled={!program || results.busy}
          onClick={() =>
            void run(async () => {
              const plans = (
                await fetchStudentAcademicPlans(
                  apiBaseUrl,
                  data.student_profile_id,
                )
              )
                .filter((item) => item.program_version_id === programId)
                .slice(0, 2);
              return plans.length === 2
                ? {
                    comparison: await compareAcademicPlans(apiBaseUrl, {
                      academic_plan_ids: plans.map((item) => item.id),
                    }),
                  }
                : { message: "请先保存至少两个规划，再比较差异。" };
            })
          }
        >
          比较最近两个规划
        </button>
        {results.plan ? (
          <>
            <p>规划状态：{statusLabel(results.plan.status)}</p>
            <ul>
              {results.plan.planned_courses.map((item) => (
                <li key={item.id}>
                  {item.term_code} · {item.course_code} · {item.credits} 学分 ·{" "}
                  {statusLabel(item.planning_status)}；{item.explanation}
                </li>
              ))}
            </ul>
            <ul>
              {results.plan.warnings.map((item) => (
                <li key={item.id}>{item.message}</li>
              ))}
            </ul>
          </>
        ) : null}
        {results.comparison ? (
          <table>
            <caption>最近两个已保存规划</caption>
            <thead>
              <tr>
                <th>方案</th>
                <th>状态</th>
                <th>学期数</th>
                <th>课程数</th>
                <th>计划学分</th>
                <th>待核对事项</th>
              </tr>
            </thead>
            <tbody>
              {results.comparison.map((item, index) => (
                <tr key={item.academic_plan_run_id}>
                  <th>方案 {index + 1}</th>
                  <td>{statusLabel(item.status)}</td>
                  <td>{item.term_count}</td>
                  <td>{item.planned_course_count}</td>
                  <td>{item.total_planned_credits}</td>
                  <td>{item.warning_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>
      <section id="what-if-planning">
        <h3>假设规划</h3>
        <p>
          只使用当前学生已审核绑定的培养方案；其他专业需先完成来源与适用性审核。
        </p>
        <button
          disabled={!program || results.busy}
          onClick={() =>
            void run(async () => {
              const scenario = await createAcademicScenario(apiBaseUrl, {
                ...student,
                scenario_name: `学业方案：${program?.name}`,
                scenario_type: "CUSTOM_COMBINATION",
                calculation_mode: "PROJECTED",
                programs: [
                  {
                    program_version_id: programId,
                    relationship_type: program!.relationship_type,
                    priority: 0,
                  },
                ],
              });
              return {
                scenario: await fetchAcademicScenarioComparison(
                  apiBaseUrl,
                  scenario.id,
                ),
              };
            })
          }
        >
          保存真实假设方案
        </button>
        <button
          disabled={results.busy}
          onClick={() =>
            void run(async () => {
              const scenarios = await fetchStudentAcademicScenarios(
                apiBaseUrl,
                data.student_profile_id,
              );
              return scenarios[0]
                ? {
                    scenario: await fetchAcademicScenarioComparison(
                      apiBaseUrl,
                      scenarios[0].id,
                    ),
                  }
                : { message: "当前学生尚无已保存的假设方案。" };
            })
          }
        >
          读取已保存假设方案
        </button>
        {results.scenario ? (
          <p>
            方案已保存。已完成学分 {results.scenario.completed_credits}
            ；额外所需学分 {results.scenario.estimated_additional_credits}
            。仍须核对学校要求。
          </p>
        ) : null}
      </section>
      <section id="sections">
        <h3>真实课节与课程选择</h3>
        <p>
          当前有 {data.section_ids.length}{" "}
          个已应用且来源可追溯的课节。缺少班次、时间待定或来源变化将在排课结果中明确说明。
        </p>
        {data.courses.map((item) => (
          <label key={item.id}>
            <input
              type="checkbox"
              checked={courseIds.includes(item.id)}
              onChange={(event) =>
                setCourseIds((current) =>
                  event.target.checked
                    ? [...current, item.id]
                    : current.filter((id) => id !== item.id),
                )
              }
            />
            {item.code} · {item.title}
          </label>
        ))}
      </section>
      <section id="schedule-builder">
        <h3>学期课表</h3>
        <label>
          <input
            type="checkbox"
            checked={noFriday}
            onChange={(event) => setNoFriday(event.target.checked)}
          />
          周五不排课
        </label>
        <button
          disabled={
            !termId || !courseIds.length || !creditPolicyValid || results.busy
          }
          onClick={() =>
            void run(async () => ({
              schedule: await createScheduleOptimization(apiBaseUrl, {
                ...student,
                term_id: termId,
                planning_mode: "CUSTOM_COURSE_SET",
                section_data_mode: "REVIEWED_IMPORTED",
                candidate_course_ids: courseIds,
                minimum_credits: minimum,
                maximum_credits: maximum,
                preferred_credits: preferred,
                excluded_days: noFriday ? ["FRIDAY"] : [],
                requested_option_count: 3,
              }),
            }))
          }
        >
          优化真实课表
        </button>
        <button
          disabled={results.busy}
          onClick={() =>
            void run(async () => {
              const runs = await fetchStudentScheduleOptimizations(
                apiBaseUrl,
                data.student_profile_id,
              );
              const selected = runs.find(
                (item) =>
                  item.term_id === termId &&
                  item.section_data_mode === "REVIEWED_IMPORTED",
              );
              return selected
                ? {
                    schedule: await fetchScheduleOptimization(
                      apiBaseUrl,
                      selected.id,
                    ),
                  }
                : { message: "当前学期尚无已保存的真实课表。" };
            })
          }
        >
          读取已保存课表
        </button>
        <p>
          座位数仅是来源读取时的参考，不代表实时可注册。所有选课操作由学生在学校门户手动完成。
        </p>
        {results.schedule ? (
          <>
            <p>
              生成时间：{results.schedule.created_at}；
              {statusLabel(results.schedule.status)}
            </p>
            {results.schedule.options.map((option) => (
              <article key={option.id}>
                <h4>
                  方案 {option.option_rank} · {option.total_credits} 学分
                </h4>
                <p>{option.explanation}</p>
                <ul>
                  {option.selected_sections.map((section) => (
                    <li key={section.id}>
                      {section.course_code} · 班次 {section.section_code} ·{" "}
                      {statusLabel(section.modality)} · 来源状态{" "}
                      {statusLabel(section.drift_status)}
                      <ul>
                        {section.meetings.map((meeting) => (
                          <li key={meeting.id}>
                            {meeting.day_of_week
                              ? statusLabel(meeting.day_of_week)
                              : "日期待核实"}{" "}
                            {meeting.start_time ?? "时间待定"}–
                            {meeting.end_time ?? "待定"}{" "}
                            {meeting.building ?? "地点待核实"} {meeting.room}{" "}
                            {meeting.timezone}
                          </li>
                        ))}
                      </ul>
                      <p>
                        来源导入：
                        {String(section.source_provenance?.import_id ?? "未知")}
                        ；读取时间：
                        {String(
                          section.source_provenance?.extraction_at ?? "未知",
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
            <ul>
              {results.schedule.conflicts.map((item) => (
                <li key={item.id}>{item.message}</li>
              ))}
              {results.schedule.warnings.map((item) => (
                <li key={item.id}>{item.message}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
    </>
  );
}
