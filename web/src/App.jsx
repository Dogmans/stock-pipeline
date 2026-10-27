import React, {useEffect, useState} from 'react';
import {ReactFlowProvider} from '@xyflow/react';
import WorkspaceShell from './WorkspaceShell.jsx';
import InvestorWorkspace from './InvestorWorkspace.jsx';
import WorkflowStudio from './WorkflowStudio.jsx';
import {researchHref, workspaceRoute} from './navigation.js';
import {useWatchlist} from './WatchlistContext.jsx';

export function WorkspacePages({route, onPage, revision = 0}) {
  return <>
    {route.researchVisited && <div hidden={route.screening}>
      <InvestorWorkspace key={route.symbol} symbol={route.symbol} page={route.page} onPage={onPage} revision={revision}/>
    </div>}
    <div className="ir-screening-page" hidden={!route.screening}>
      {route.screeningVisited && <ReactFlowProvider><WorkflowStudio active={route.screening}/></ReactFlowProvider>}
    </div>
  </>;
}

export default function App({initialHash = globalThis.window?.location.hash || ''}) {
  const [route, setRoute] = useState(() => workspaceRoute(initialHash));
  const [revision, setRevision] = useState(0);
  const {notify} = useWatchlist();
  useEffect(() => {
    const change = () => setRoute(previous => workspaceRoute(window.location.hash, previous));
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  const openSymbol = symbol => {window.location.hash = researchHref(symbol);};
  const openPage = page => {window.location.hash = page === 'screening' ? '#screening' : researchHref(route.symbol, page);};

  return <WorkspaceShell route={route} onSymbol={openSymbol} onPage={openPage} onReload={() => {
    setRevision(value => value + 1);notify('Reloading data. FMP cache windows still apply.');
  }}>
    <WorkspacePages route={route} onPage={openPage} revision={revision}/>
  </WorkspaceShell>;
}
