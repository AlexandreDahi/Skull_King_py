import { RenderMode, ServerRoute } from '@angular/ssr';


export const serverRoutes: ServerRoute[] = [
  {
    path: '**',
    renderMode: RenderMode.Prerender
  },
  {
  path: 'join-room/:id',
  renderMode: RenderMode.Client
  },
  {
    path: 'lobby/:id',
    renderMode: RenderMode.Client
  },
  {
    path: 'game/:id',
    renderMode: RenderMode.Client
  }
];
