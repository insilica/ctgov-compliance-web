import type { ReactNode } from 'react';
import { Grid, GridContainer } from '@trussworks/react-uswds';

export type FormLayoutProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function FormLayout({ title, description, actions, children }: FormLayoutProps) {
  return (
    <section className="usa-section">
      <GridContainer>
        <Grid row gap="md" className="margin-top-4">
          <Grid tablet={{ col: 7 }}>
            <h2 className="margin-bottom-05">{title}</h2>
            {description && <p className="usa-prose text-base-light">{description}</p>}
          </Grid>
          {actions && (
            <Grid tablet={{ col: 5 }} className="display-flex flex-justify-end">
              {actions}
            </Grid>
          )}
        </Grid>
        <Grid row>
          <Grid tablet={{ col: 12 }}>{children}</Grid>
        </Grid>
      </GridContainer>
    </section>
  );
}
